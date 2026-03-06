const express = require("express");
const axios = require("axios");
const router = express.Router();

router.post("/recommend", async (req, res) => {
  const response = await axios.post("http://127.0.0.1:8000/recommend", {
    interests: req.body.interests
  });
  res.json(response.data);
});

module.exports = router;