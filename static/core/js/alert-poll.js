/* PET Digital — general alarm propagation.
 *
 * Every authenticated page polls dashboard:alert_status every few seconds
 * (see templates/base.html). When it finds an active, unended
 * EvacuationEvent for the viewer's own unit, it shows the same full-screen
 * "EVACUAÇÃO ACIONADA" overlay the Gestor dashboard server-renders
 * (pulsing beacons, flashing background, dynamic reason/unit/who-triggered
 * text) and plays the recorded siren (static/core/audio/alarmeevacuacao.mp3).
 * This is the web-app stand-in for what a future native app would instead
 * receive as a real push notification the moment the alarm is triggered,
 * with no polling delay.
 *
 * PHYSICAL/BLUETOOTH EXTENSION POINT
 * -----------------------------------
 * This server has no Bluetooth radio of its own — a real BLE siren can
 * only be driven by something physically near it (a phone or gateway).
 * PetAlert.onActiveChange(callback) is exposed for exactly that: a future
 * native app (or a browser that supports the Web Bluetooth API, which
 * today means Chrome/Edge on Android — not iOS Safari, not this hosted
 * page's own sandboxed context) can register a callback here and, inside
 * it, connect to a paired BLE siren via navigator.bluetooth and write to
 * its alert characteristic. Physical gateways that aren't co-located with
 * a browser (a Raspberry Pi wired to a relay, for instance) should
 * instead subscribe as a dashboard.models.PhysicalAlertEndpoint, which
 * gets an HTTP webhook the instant the alarm triggers/silences/ends —
 * see dashboard/webhooks.py. Example (illustrative, not wired up because
 * it needs real hardware to test against):
 *
 *   PetAlert.onActiveChange(async (active, alertData) => {
 *     if (!active || !navigator.bluetooth) return;
 *     const device = await navigator.bluetooth.requestDevice({
 *       filters: [{ services: ['<siren-service-uuid>'] }],
 *     });
 *     const server = await device.gatt.connect();
 *     const service = await server.getPrimaryService('<siren-service-uuid>');
 *     const characteristic = await service.getCharacteristic('<alert-characteristic-uuid>');
 *     await characteristic.writeValue(new Uint8Array([1]));
 *   });
 */
window.PetAlert = (function () {
  const POLL_INTERVAL_MS = 5000;
  const STATUS_URL = "/gestor/alerta/status/";
  const SIREN_URL = "/static/core/audio/alarmeevacuacao.mp3";

  let ownOverlayEl = null; // only set when we injected it ourselves
  let sirenAudio = null;
  let currentEventId = null;
  let acknowledgedEventId = null;
  const activeChangeListeners = [];

  function serverRenderedOverlay() {
    // The Gestor dashboard server-renders its own overlay (same markup,
    // plus "silenciar sirene" / "encerrar evacuação") when it loads — on
    // that page we drive only the siren, not a second competing overlay.
    return document.querySelector(".evacuation-overlay:not(#pet-alert-overlay)");
  }

  function ensureOwnOverlay() {
    if (ownOverlayEl) return ownOverlayEl;
    ownOverlayEl = document.createElement("div");
    ownOverlayEl.id = "pet-alert-overlay";
    ownOverlayEl.className = "evacuation-overlay";
    ownOverlayEl.style.display = "none";
    ownOverlayEl.innerHTML =
      '<div class="evacuation-beacons">' +
      '<span class="evacuation-beacon"></span><span class="evacuation-beacon"></span><span class="evacuation-beacon"></span>' +
      "</div>" +
      '<div class="evacuation-title">EVACUAÇÃO ACIONADA</div>' +
      '<div class="evacuation-detail" id="pet-alert-reason"></div>' +
      '<div class="evacuation-meta" id="pet-alert-meta"></div>' +
      '<div class="evacuation-actions" style="display:flex;gap:14px;margin-top:10px;flex-wrap:wrap;justify-content:center;">' +
      '<button type="button" id="pet-alert-ack" class="btn" style="height:46px;padding:0 22px;' +
      'background:#fff;color:#8e2020;border-color:#fff;font-size:15px;">Estou ciente</button>' +
      "</div>";
    document.body.appendChild(ownOverlayEl);
    ownOverlayEl.querySelector("#pet-alert-ack").addEventListener("click", acknowledge);
    return ownOverlayEl;
  }

  function showOverlay(data) {
    if (serverRenderedOverlay()) return; // already visible, server-controlled
    const overlay = ensureOwnOverlay();
    overlay.querySelector("#pet-alert-reason").textContent = data.reason + " — unidade " + data.unit;
    overlay.querySelector("#pet-alert-meta").innerHTML =
      "acionado às " +
      data.triggered_at_label +
      " por " +
      data.triggered_by +
      "<br>sirene local ativada · brigada e portaria notificadas<br>equipes das frentes ativas recebendo alerta no app";
    overlay.style.display = "flex";
  }

  function hideOwnOverlay() {
    if (ownOverlayEl) ownOverlayEl.style.display = "none";
  }

  function startSiren() {
    if (sirenAudio) return;
    sirenAudio = new Audio(SIREN_URL);
    sirenAudio.loop = true;
    // Autoplay is blocked before any user gesture on the page — the
    // overlay still shows reliably either way, only the sound may start
    // silently until the viewer has interacted with the page once.
    sirenAudio.play().catch(() => {});
  }

  function stopSiren() {
    if (sirenAudio) {
      sirenAudio.pause();
      sirenAudio.currentTime = 0;
      sirenAudio = null;
    }
  }

  function acknowledge() {
    acknowledgedEventId = currentEventId;
    hideOwnOverlay();
    stopSiren();
  }

  function notifyListeners(active, data) {
    activeChangeListeners.forEach((callback) => {
      try {
        callback(active, data);
      } catch (e) {}
    });
  }

  async function poll() {
    let data;
    try {
      const response = await fetch(STATUS_URL, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!response.ok) return;
      data = await response.json();
    } catch (e) {
      return;
    }

    if (!data.active) {
      const wasActive = currentEventId !== null;
      currentEventId = null;
      acknowledgedEventId = null;
      hideOwnOverlay();
      stopSiren();
      if (wasActive) notifyListeners(false, null);
      return;
    }

    const isNewEvent = data.id !== currentEventId;
    currentEventId = data.id;
    if (isNewEvent) {
      acknowledgedEventId = null;
      notifyListeners(true, data);
    }

    const locallyAcknowledged = currentEventId === acknowledgedEventId;
    // A manager's "silenciar sirene" mutes the sound for everyone, but the
    // event is still active — the overlay stays up until it's resolved
    // ("registrar evacuação concluída") or this viewer acknowledges it.
    if (data.silenced || locallyAcknowledged) {
      stopSiren();
    } else {
      startSiren();
    }
    if (locallyAcknowledged) {
      hideOwnOverlay();
    } else {
      showOverlay(data);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    poll();
    setInterval(poll, POLL_INTERVAL_MS);
  });

  return {
    acknowledge,
    onActiveChange(callback) {
      activeChangeListeners.push(callback);
    },
  };
})();
