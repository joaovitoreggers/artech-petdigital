/* PET Digital — vanilla JS helpers for the "Nova PET" field wizard.
   No build step, no framework: matches the rest of the project. */
window.PetWizard = (function () {
  function csrfToken() {
    const input = document.querySelector('input[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  function captureLocation(statusElementId, onSuccess) {
    const status = document.getElementById(statusElementId);
    if (!navigator.geolocation) {
      if (status) status.textContent = 'geolocalização não disponível neste navegador';
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        const latField = document.getElementById('id_latitude');
        const lngField = document.getElementById('id_longitude');
        const accField = document.getElementById('id_location_accuracy_meters');
        if (latField) latField.value = latitude;
        if (lngField) lngField.value = longitude;
        if (accField) accField.value = accuracy;
        if (status) {
          status.textContent = `${latitude.toFixed(4)}, ${longitude.toFixed(4)} · precisão ${Math.round(accuracy)} m`;
        }
        if (onSuccess) onSuccess({ latitude, longitude, accuracy });
      },
      () => {
        if (status) status.textContent = 'não foi possível obter a localização — verifique a permissão do navegador';
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function setupSignaturePad(canvas) {
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#1d1f20';
    let drawing = false;
    let hasDrawn = false;

    const position = (event) => {
      const rect = canvas.getBoundingClientRect();
      return [
        ((event.clientX - rect.left) * canvas.width) / rect.width,
        ((event.clientY - rect.top) * canvas.height) / rect.height,
      ];
    };

    canvas.addEventListener('pointerdown', (event) => {
      drawing = true;
      canvas.setPointerCapture(event.pointerId);
      const [x, y] = position(event);
      ctx.beginPath();
      ctx.moveTo(x, y);
      event.preventDefault();
    });
    canvas.addEventListener('pointermove', (event) => {
      if (!drawing) return;
      const [x, y] = position(event);
      ctx.lineTo(x, y);
      ctx.stroke();
      hasDrawn = true;
      event.preventDefault();
    });
    const stop = () => { drawing = false; };
    canvas.addEventListener('pointerup', stop);
    canvas.addEventListener('pointerleave', stop);

    return {
      clear() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        hasDrawn = false;
      },
      hasDrawn: () => hasDrawn,
      toDataURL: () => canvas.toDataURL('image/png'),
    };
  }

  function prepareSignatureStep(options) {
    const pads = {};
    options.canvases.forEach((canvasId) => {
      const canvas = document.getElementById(canvasId);
      if (canvas) pads[canvasId] = setupSignaturePad(canvas);
    });

    document.querySelectorAll('[data-clear-signature]').forEach((button) => {
      button.addEventListener('click', () => {
        const canvasId = button.getAttribute('data-clear-signature');
        pads[canvasId].clear();
        const statusId = options.statusFieldsByCanvas[canvasId];
        if (statusId) document.getElementById(statusId).textContent = 'assine no quadro acima';
      });
    });

    Object.keys(pads).forEach((canvasId) => {
      const canvas = document.getElementById(canvasId);
      const statusId = options.statusFieldsByCanvas[canvasId];
      canvas.addEventListener('pointerup', () => {
        if (statusId && pads[canvasId].hasDrawn()) {
          document.getElementById(statusId).textContent = 'assinatura capturada';
        }
      });
    });

    captureLocation('__signature_gps_silent__', ({ latitude, longitude }) => {
      document.getElementById(options.latitudeFieldId).value = latitude;
      document.getElementById(options.longitudeFieldId).value = longitude;
    });

    const form = document.getElementById(options.formId);
    form.addEventListener('submit', (event) => {
      const submitter = event.submitter;
      if (!submitter || submitter.name !== options.submitterName) return;

      const missing = Object.keys(pads).filter((canvasId) => !pads[canvasId].hasDrawn());
      if (missing.length) {
        event.preventDefault();
        alert('Colete as duas assinaturas antes de emitir a PET.');
        return;
      }
      Object.entries(options.hiddenFieldsByCanvas).forEach(([canvasId, fieldId]) => {
        document.getElementById(fieldId).value = pads[canvasId].toDataURL();
      });
    });
  }

  function startBadgeScanner({ readerId, statusId, scanUrl, targetId }) {
    if (!window.Html5Qrcode) {
      document.getElementById(statusId).textContent = 'leitor de QR indisponível neste navegador';
      return;
    }
    const scanner = new Html5Qrcode(readerId);
    const status = document.getElementById(statusId);
    let busy = false;

    scanner
      .start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: 220 },
        (decodedText) => {
          if (busy) return;
          busy = true;
          status.textContent = 'crachá lido, consultando cadastro…';
          fetch(scanUrl, {
            method: 'POST',
            headers: {
              'X-CSRFToken': csrfToken(),
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `token=${encodeURIComponent(decodedText)}`,
          })
            .then((response) => response.text())
            .then((html) => {
              document.getElementById(targetId).innerHTML = html;
              status.textContent = 'aponte a câmera para o próximo crachá';
              busy = false;
            })
            .catch(() => {
              status.textContent = 'falha ao consultar o cadastro — tente novamente';
              busy = false;
            });
        }
      )
      .catch(() => {
        status.textContent = 'não foi possível acessar a câmera — verifique a permissão do navegador';
      });
  }

  return { captureLocation, prepareSignatureStep, startBadgeScanner };
})();
