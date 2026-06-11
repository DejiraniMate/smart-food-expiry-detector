// ============================================================
// Smart Food Expiry Detector — main.js
// Client-side helper: live expiry date preview in the Add form
// ============================================================

/**
 * Calculates and displays the expiry date as the user
 * fills in the purchase_date and shelf_life fields.
 * This is purely cosmetic — the real calculation happens
 * server-side in app.py (/add route).
 */

(function () {
  'use strict';

  // Get form fields
  var purchaseDateInput = document.getElementById('purchase_date');
  var shelfLifeInput    = document.getElementById('shelf_life');
  var previewBox        = document.getElementById('expiryPreview');
  var expiryDisplay     = document.getElementById('expiryDateDisplay');

  // Only run on pages that have the form
  if (!purchaseDateInput || !shelfLifeInput) return;

  function updatePreview() {
    var purchaseVal  = purchaseDateInput.value;   // "YYYY-MM-DD"
    var shelfLifeVal = parseInt(shelfLifeInput.value, 10);

    if (purchaseVal && !isNaN(shelfLifeVal) && shelfLifeVal > 0) {
      // Parse without timezone shift (treat as local date)
      var parts = purchaseVal.split('-');
      var purchaseDate = new Date(
        parseInt(parts[0]),
        parseInt(parts[1]) - 1,
        parseInt(parts[2])
      );

      // Add shelf_life days
      purchaseDate.setDate(purchaseDate.getDate() + shelfLifeVal);

      // Format as YYYY-MM-DD
      var year  = purchaseDate.getFullYear();
      var month = String(purchaseDate.getMonth() + 1).padStart(2, '0');
      var day   = String(purchaseDate.getDate()).padStart(2, '0');
      var expiryStr = year + '-' + month + '-' + day;

      expiryDisplay.textContent = expiryStr;
      previewBox.style.display  = 'block';
    } else {
      previewBox.style.display = 'none';
    }
  }

  // Attach listeners to both inputs
  purchaseDateInput.addEventListener('change', updatePreview);
  shelfLifeInput.addEventListener('input',  updatePreview);

  // ── Set today as default purchase date ──────────────────
  var today = new Date();
  var yyyy  = today.getFullYear();
  var mm    = String(today.getMonth() + 1).padStart(2, '0');
  var dd    = String(today.getDate()).padStart(2, '0');
  purchaseDateInput.value = yyyy + '-' + mm + '-' + dd;
  updatePreview();   // Trigger preview if shelf life already has a value

})();
