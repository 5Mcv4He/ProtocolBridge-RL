// Four native capabilities; all state, authority and grading remain in the host controller.
import net from 'node:net';
import fs from 'node:fs';
export const name = 'protocolbridge-native-tools-v1';
export const inject = ['tools'];
function exchange(socketPath, packet) {
  return new Promise((resolve, reject) => {
    let buffer = '';
    const socket = net.createConnection(socketPath);
    socket.setTimeout(240000);
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
export function apply(ctx, config) {
  const definitions = [
    ['read', 'Read spec.md or the current editable artifact.', {file:{type:'string',enum:['spec.md',config.filename]}}, ['file']],
    ['edit', 'Replace the editable artifact with these exact complete contents.', {content:{type:'string'}}, ['content']],
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
      async execute(args, execution) {
        const reply = await exchange(config.socket, {kind:'tool_request',call_id:execution.callId,name,arguments:args});
        if (reply.stop === true) execution.concludeTurn();
        return JSON.stringify(reply.observation);
      },
    });
  }
  // Trusted startup attestation only; not a model-readable action.
  fs.writeFileSync(config.ready, JSON.stringify({names:ctx.tools.definitions().map(x=>x.name).sort()}));
}
