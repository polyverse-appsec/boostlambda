const axios = require('axios');

const payload = { input: 'example input' };

axios.post('http://127.0.0.1:8000/explain', payload)
  .then(response => {
    console.log(response.data);
  })
  .catch(error => {
    console.error(error);
  });

