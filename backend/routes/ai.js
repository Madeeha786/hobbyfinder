const express = require("express");
const axios = require("axios");
const { Pool } = require("pg");

const router = express.Router();

const pool = new Pool({
  user: "postgres",
  host: "localhost",
  database: "hobbyfinder",
  password: "hobbyfinder",
  port: 5432
});

// --- RECOMMENDATION ROUTE ---
router.post("/recommend", async (req, res) => {
    try {
        const interests = req.body.interests;
        // user_id is no longer needed here since we aren't saving to the DB automatically anymore

        /* Call Flask AI */
        const response = await axios.post("http://127.0.0.1:8000/recommend", interests);
        const recommendations = response.data.recommendations;

        // Note: The loop that automatically inserted into PostgreSQL has been removed!

        res.json(recommendations);

    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "AI recommendation failed" });
    }
});


router.post("/chat", async (req, res) => {
    try {
        // 1. Grab the user's chat message from the frontend request
        const message = req.body.message;

        if (!message) {
            return res.status(400).json({ error: "Message is required" });
        }

        // 2. Forward the message to your Python Flask microservice
        const response = await axios.post("http://127.0.0.1:8000/chat", {
            message: message
        });

        // 3. Send the structured JSON recommendations back to the frontend
        res.json(response.data);

    } catch (err) {
        console.error("Chat API Error:", err.message);
        res.status(500).json({ error: "Failed to communicate with AI chat service" });
    }
});

module.exports = router;