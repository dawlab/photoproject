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

// Resize image client-side using Canvas, returns a Blob (webp)
function resizeImage(file, maxSide, quality = 0.82) {
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      if (width > maxSide || height > maxSide) {
        if (width >= height) { height = Math.round(height * maxSide / width); width = maxSide; }
        else { width = Math.round(width * maxSide / height); height = maxSide; }
      }
      const canvas = document.createElement('canvas');
      canvas.width = width; canvas.height = height;
      canvas.getContext('2d').drawImage(img, 0, 0, width, height);
      canvas.toBlob(resolve, 'image/webp', quality);
    };
    img.src = URL.createObjectURL(file);
  });
}

// Get original image dimensions
function getImageSize(file) {
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => resolve({ width: null, height: null });
    img.src = URL.createObjectURL(file);
  });
}
