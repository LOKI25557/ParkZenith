const fs = require('fs');
const path = require('path');

const walkSync = function(dir, filelist) {
  var files = fs.readdirSync(dir);
  filelist = filelist || [];
  files.forEach(function(file) {
    if (fs.statSync(dir + '/' + file).isDirectory()) {
      filelist = walkSync(dir + '/' + file, filelist);
    }
    else {
      filelist.push(dir + '/' + file);
    }
  });
  return filelist;
};

const allFiles = walkSync(path.join(__dirname, 'src'), []).filter(f => f.endsWith('.tsx'));
allFiles.forEach(file => {
  let content = fs.readFileSync(file, 'utf8');
  content = content.replace(/import React from 'react';\r?\n/g, '');
  content = content.replace(/import React, /g, 'import ');
  fs.writeFileSync(file, content);
});
console.log('Removed unused React imports');
