
const jwt = require('jsonwebtoken');

const ok = (token, key) => {
  // ok: jwt-decode-without-verify
  jwt.verify(token, key);
  if (jwt.decode(token, true).param === true) {
    console.log('token is valid');
  }
};
