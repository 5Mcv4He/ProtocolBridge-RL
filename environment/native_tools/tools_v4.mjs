// Four native capabilities; all state, authority and grading remain in the host controller.
import net from 'node:net';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
export const name = 'protocolbridge-native-tools-v4';
export const inject = ['tools'];
function exchange(socketPath, packet) {
  return new Promise((resolve, reject) => {
    let buffer = '';
    const socket = net.createConnection(socketPath);
    socket.setTimeout(2520000);
    socket.on('connect', () => socket.write(JSON.stringify(packet) + '\n'));
    socket.on('data', chunk => {
      buffer += chunk.toString();
      if (Buffer.byteLength(buffer) > 262144) { socket.destroy(); reject(new Error('controller_output_limit')); return; }
      const end = buffer.indexOf('\n');
      if (end >= 0) {
        try { const reply = JSON.parse(buffer.slice(0, end)); socket.end(); resolve(reply); }
        catch { socket.destroy(); reject(new Error('controller_protocol_error')); }
      }
    });
    socket.on('close', () => reject(new Error('controller_closed')));
    socket.on('timeout', () => { socket.destroy(); reject(new Error('controller_timeout')); });
    socket.on('error', () => reject(new Error('controller_unavailable')));
  });
}
export async function apply(ctx, config) {
  const definitions = [
    ['read', 'Read spec.md or the current editable artifact.', {file:{type:'string',enum:['spec.md',config.filename]}}, ['file']],
    ['edit', 'Replace the named editable artifact with these exact complete contents. Only the fixed task filename is allowed.', {file:{type:'string',enum:[config.filename]},content:{type:'string'}}, ['file','content']],
    ['test', 'Run the public checker against the current artifact; consumes one allowed public check.', {}, []],
    ['submit', 'Freeze the current artifact and stop solving. Independent final grading happens afterwards.', {}, []],
  ];
  for (const [name, description, properties, required] of definitions) {
    ctx.tools.register({
      name, description,
      parameters: {type:'object',properties,required,additionalProperties:false},
      output: {schema:{type:'string'},render:(_args,value)=>[{type:'text',text:value}]},
      // Deliberately exclusive: native batches retain model order and cannot race edits/tests.
      isConcurrencySafe:()=>false,
      async execute(_args, execution) {
        const reply=replies.get(execution.callId);
        if (!reply) throw new Error('unmediated_dispatch');
        if (reply.stop === true) execution.concludeTurn();
        return JSON.stringify(reply.observation);
      },
    });
  }
  // Account before the SDK resolves names or parses/dispatches tool bodies.
  const replies = new Map();
  ctx.on('tools/pre-execute', async execution => {
    const calls = execution.agent
      ? execution.agent.session.deriveMessages().filter(x=>x.role==='assistant').flatMap(x=>x.content).filter(x=>x.type==='tool-call')
      : (config.mechanism_calls ?? []);
    const originals = calls.filter(x=>x.id===execution.callId);
    if (originals.length !== 1) throw new Error('unbound_native_call');
    const raw = originals[0];
    const reply = await exchange(config.socket, {
      kind:'tool_request',call_id:execution.callId,name:raw.name,arguments:raw.arguments,
    });
    replies.set(execution.callId,reply);
    const known = definitions.some(x=>x[0]===raw.name);
    if (!known) return {kind:'deny',reason:JSON.stringify(reply.observation)};
    return {kind:'allow'};
  });
  let requests = 0;
  ctx.on('agent/request', async (event, next) => {
    // This hook is before prepareCall/stream; exhaustion starts no new API call.
    const messages = event.agent.session.deriveMessages().filter(x => x.role === 'tool');
    const prior = messages.map(x => ({call_id:x.toolCallId,
      text_sha256:createHash('sha256').update(x.content.filter(b=>b.type==='text').map(b=>b.text).join('')).digest('hex')}));
    const reply = await exchange(config.socket,{kind:'model_request',call_id:'request-'+(++requests),
      request_index:requests,prior_tool_results:prior});
    if (reply.stop === true || requests > config.max_model_requests) throw new Error('model_request_budget');
    return next();
  });
  if (config.mechanism_calls) {
    // Administrator-controlled zero-API exercise of the installed SDK executor.
    // This is not a model tool and never supplied to research episodes.
    const deadline=Date.now()+20000;
    while (true) {
      try { ctx.tools.selectExecutor(); break; }
      catch (error) { if(Date.now()>deadline) throw error; await new Promise(resolve=>setTimeout(resolve,50)); }
    }
    const result=await ctx.tools.execute({calls:config.mechanism_calls,signal:new AbortController().signal});
    fs.writeFileSync(config.ready+'.mechanism.json',JSON.stringify(result));
  }
  fs.writeFileSync(config.ready, JSON.stringify({names:ctx.tools.definitions().map(x=>x.name).sort()}));
}
