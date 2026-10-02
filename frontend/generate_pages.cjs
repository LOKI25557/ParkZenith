const fs = require('fs');
const path = require('path');
const pages = ['Home', 'Login', 'Register', 'Dashboard', 'Parking', 'ParkingDetail', 'Reservations', 'ReservationDetail', 'Sessions', 'Payments', 'Predictions', 'Profile', 'Admin'];
const dir = path.join(__dirname, 'src', 'pages');
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
pages.forEach(p => {
  const code = `import React from 'react';\n\nconst ${p} = () => {\n  return <div>${p} Page Placeholder</div>;\n};\n\nexport default ${p};\n`;
  fs.writeFileSync(path.join(dir, p + '.tsx'), code);
});
console.log('Pages created successfully.');
