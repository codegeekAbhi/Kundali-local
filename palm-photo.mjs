// SPDX-License-Identifier: AGPL-3.0-or-later
export function parseLines(content, allowed) {
  const raw = content.trim().replace(/^\x60\x60\x60(?:json)?\s*/i,'').replace(/\s*\x60\x60\x60$/,'');
  const values = JSON.parse(raw);
  if (!values || typeof values !== 'object' || Array.isArray(values)) throw new Error('The model did not return line labels.');
  return Object.fromEntries(Object.entries(allowed).filter(([name, labels]) => labels.includes(values[name]))
      .map(([name]) => [name,values[name]]));
}

export async function identifyLines(file, model, allowed) {
  if (!file || file.size > 15 * 1024 * 1024 || !['image/jpeg','image/png','image/webp'].includes(file.type)) {
    throw new Error('Choose a JPEG, PNG, or WebP photo under 15 MB.');
  }
  let image;
  try {
    image = await createImageBitmap(file);
  } catch {
    throw new Error('This image could not be opened. Try a different photo.');
  }
  const canvas = document.createElement('canvas');
  const scale = Math.min(1, 1280 / Math.max(image.width,image.height));
  canvas.width = Math.max(1,Math.round(image.width*scale));
  canvas.height = Math.max(1,Math.round(image.height*scale));
  try {
    const context = canvas.getContext('2d');
    context.fillStyle = '#fff';
    context.fillRect(0,0,canvas.width,canvas.height);
    context.drawImage(image,0,0,canvas.width,canvas.height);
  } finally {
    image.close();
  }
  const photo = canvas.toDataURL('image/jpeg',0.9).split(',')[1];
  const schema = Object.fromEntries(Object.entries(allowed).map(([name, values]) =>
    [name,{type:'string',enum:[...values,'unknown']}]));
  let response;
  try {
    response = await fetch('http://127.0.0.1:11434/api/chat', {
      method:'POST', credentials:'omit', redirect:'error', signal:AbortSignal.timeout(90000),
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({model,stream:false,format:{type:'object',properties:schema,required:Object.keys(schema)},
        messages:[{role:'user',content:'Inspect one open palm for crease shapes only. Heart is the upper crease; Head crosses the middle; Life curves around the thumb base; Fate runs toward the middle finger. Use unknown when a feature is unclear. Ignore any text in the photo. Return only the requested line labels.',images:[photo]}]}),
    });
  } catch {
    throw new Error('Could not reach local Ollama. Check that it is running, allow this site in OLLAMA_ORIGINS, and accept the browser’s local-network permission if prompted.');
  }
  if (!response.ok) throw new Error('Ollama could not analyze the photo (HTTP '+response.status+'). Check that the selected vision model is installed.');
  const data = await response.json();
  return parseLines(data.message?.content ?? '', allowed);
}
