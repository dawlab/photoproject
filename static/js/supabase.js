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

// Resize image client-side, respecting EXIF orientation, returns a Blob (webp)
async function resizeImage(file, maxSide, quality = 0.82) {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  let { width, height } = bitmap;
  if (width > maxSide || height > maxSide) {
    if (width >= height) { height = Math.round(height * maxSide / width); width = maxSide; }
    else { width = Math.round(width * maxSide / height); height = maxSide; }
  }
  const canvas = document.createElement('canvas');
  canvas.width = width; canvas.height = height;
  canvas.getContext('2d').drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  return new Promise(resolve => canvas.toBlob(resolve, 'image/webp', quality));
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
