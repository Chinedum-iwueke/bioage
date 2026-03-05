(() => {
  const heightInput = document.getElementById('height_cm');
  const weightInput = document.getElementById('weight_kg');
  const bmiInput = document.getElementById('bmi');

  if (!heightInput || !weightInput || !bmiInput) {
    return;
  }

  let bmiAutofilled = false;

  const inRange = (value, min, max) => Number.isFinite(value) && value >= min && value <= max;

  const maybeAutofillBMI = () => {
    const heightCm = parseFloat(heightInput.value);
    const weightKg = parseFloat(weightInput.value);

    if (!inRange(heightCm, 50, 300) || !inRange(weightKg, 10, 500)) {
      return;
    }

    const heightM = heightCm / 100;
    const bmi = weightKg / (heightM * heightM);
    bmiInput.value = bmi.toFixed(1);
    bmiAutofilled = true;
  };

  heightInput.addEventListener('input', maybeAutofillBMI);
  weightInput.addEventListener('input', maybeAutofillBMI);

  bmiInput.addEventListener('input', () => {
    if (document.activeElement === bmiInput && bmiAutofilled) {
      bmiAutofilled = false;
    }
  });
})();
