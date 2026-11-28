// Driver page: watch the phone's GPS and send the latest point to the server every 5 seconds.
(function () {
  const root = document.getElementById('driver');
  if (!root) return;
  const SEND_EVERY_MS = 5000;
  const url = root.dataset.url, csrf = root.dataset.csrf;
  const startBtn = document.getElementById('startBtn'), stopBtn = document.getElementById('stopBtn');
  const statusEl = document.getElementById('status'), lastEl = document.getElementById('lastPoint');
  let watchId = null, timer = null, latest = null, sending = false;

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = 'driver-status' + (kind ? ' ' + kind : '');
  }

  function setSharing(on) {
    startBtn.hidden = on;
    stopBtn.hidden = !on;
  }

  function start() {
    if (!('geolocation' in navigator)) return setStatus('This browser cannot share its location.', 'error');
    if (!window.isSecureContext) return setStatus('Location only works over HTTPS (or on localhost).', 'error');
    setSharing(true);
    setStatus('Waiting for GPS signal…', 'wait');
    watchId = navigator.geolocation.watchPosition(onPosition, onError,
      {enableHighAccuracy: true, maximumAge: SEND_EVERY_MS, timeout: 20000});
    // keep sending the last point even when the bus stands still, so it stays "online" on the map
    timer = setInterval(send, SEND_EVERY_MS);
  }

  function stop(message, kind) {
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    clearInterval(timer);
    watchId = timer = latest = null;
    setSharing(false);
    setStatus(message || 'Sharing stopped.', kind);
  }

  function onPosition(p) {
    const first = latest === null;
    latest = {lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy)};
    if (first) send();  // don't make the driver wait 5 seconds for the first point
  }

  function onError(err) {
    if (err.code === err.PERMISSION_DENIED) {
      stop('Location permission denied. Allow location for this site in your browser settings, then press Start.', 'error');
    } else if (err.code === err.POSITION_UNAVAILABLE) {
      setStatus('No GPS signal. Still trying…', 'warn');
    } else {
      setStatus('GPS is slow to answer. Still trying…', 'warn');
    }
  }

  async function send() {
    if (!latest || sending) return;
    sending = true;
    const point = latest;
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
        body: JSON.stringify({lat: point.lat, lng: point.lng}),
      });
      const data = await r.json().catch(() => ({}));
      if (r.ok) {
        setStatus('Sharing. Last sent at ' + new Date().toLocaleTimeString() + '.', 'ok');
        lastEl.textContent = `${point.lat.toFixed(5)}, ${point.lng.toFixed(5)} (±${point.accuracy} m)`;
      } else if (r.status === 401 || r.status === 403) {
        stop(data.error || 'You are not allowed to send this bus\'s position. Log in again.', 'error');
      } else {
        setStatus(data.error || `Server error (${r.status}). Will retry.`, 'warn');
      }
    } catch (e) {
      setStatus('No internet connection. Will retry in 5 seconds.', 'warn');
    } finally {
      sending = false;
    }
  }

  startBtn.addEventListener('click', start);
  stopBtn.addEventListener('click', () => stop());
})();
