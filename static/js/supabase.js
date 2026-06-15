const SUPABASE_URL = 'https://bbhatybqqpnanmzcnhve.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJiaGF0eWJxcXBuYW5temNuaHZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEzNjQ1NDEsImV4cCI6MjA5Njk0MDU0MX0.7z_HbWnCydjls6d4qV2kHoko6A3GVYfucYfOIG_ye8o';

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

function photoUrl(filename) {
  if (!filename) return '';
  return sb.storage.from('photos').getPublicUrl(filename).data.publicUrl;
}

function thumbUrl(filename) {
  if (!filename) return '';
  return sb.storage.from('thumbnails').getPublicUrl(filename).data.publicUrl;
}

// Resize image client-side, respecting EXIF orientation, returns a Blob (webp).
// Uses multi-step halving for sharp results (avoids single-step blurriness).
async function resizeImage(file, maxSide, quality = 0.82) {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  let srcW = bitmap.width, srcH = bitmap.height;

  let targetW = srcW, targetH = srcH;
  if (targetW > maxSide || targetH > maxSide) {
    if (targetW >= targetH) { targetH = Math.round(targetH * maxSide / targetW); targetW = maxSide; }
    else { targetW = Math.round(targetW * maxSide / targetH); targetH = maxSide; }
  }

  // Draw original into canvas
  let canvas = document.createElement('canvas');
  canvas.width = srcW; canvas.height = srcH;
  canvas.getContext('2d').drawImage(bitmap, 0, 0);
  bitmap.close();

  // Halve dimensions step by step until we're within 2x of target
  let curW = srcW, curH = srcH;
  while (curW > targetW * 2 || curH > targetH * 2) {
    const nextW = Math.max(Math.ceil(curW / 2), targetW);
    const nextH = Math.max(Math.ceil(curH / 2), targetH);
    const tmp = document.createElement('canvas');
    tmp.width = nextW; tmp.height = nextH;
    const ctx = tmp.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(canvas, 0, 0, nextW, nextH);
    canvas = tmp; curW = nextW; curH = nextH;
  }

  // Final step with high quality
  const final = document.createElement('canvas');
  final.width = targetW; final.height = targetH;
  const ctx = final.getContext('2d');
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(canvas, 0, 0, targetW, targetH);

  return new Promise(resolve => final.toBlob(resolve, 'image/webp', quality));
}

// Get image dimensions respecting EXIF orientation
async function getImageSize(file) {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const { width, height } = bitmap;
    bitmap.close();
    return { width, height };
  } catch { return { width: null, height: null }; }
}
