const express = require("express");
const { Pool } = require("pg");
const router = express.Router();

const pool = new Pool({
  user: "postgres",
  host: "localhost",
  database: "hobbyfinder",
  password: "hobbyfinder",
  port: 5432
});

// Get the entire catalog
router.get("/", async (req, res) => {
  try {
    const result = await pool.query("SELECT * FROM catalog");
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to fetch catalog" });
  }
});

// ... existing GET routes ...

// NEW: Manually save a specific recommendation for a user
router.post("/save", async (req, res) => {
    try {
        const { user_id, title } = req.body;

        if (!user_id || !title) {
            return res.status(400).json({ error: "user_id and title are required" });
        }

        // 1. Find the catalog item ID by its title
        const catalogItem = await pool.query(
            "SELECT id FROM catalog WHERE title = $1",
            [title]
        );

        if (catalogItem.rows.length === 0) {
            return res.status(404).json({ error: "Item not found in catalog" });
        }

        const catalog_id = catalogItem.rows[0].id;

        // 2. Check if the user already saved this item to prevent duplicates
        const existing = await pool.query(
            "SELECT * FROM recommendations WHERE user_id = $1 AND catalog_id = $2",
            [user_id, catalog_id]
        );

        if (existing.rows.length > 0) {
            return res.status(400).json({ message: "You already saved this pick!" });
        }

        // 3. Insert the new saved pick into the database
        await pool.query(
            "INSERT INTO recommendations (user_id, catalog_id) VALUES ($1, $2)",
            [user_id, catalog_id]
        );

        res.status(201).json({ message: "Pick saved successfully!" });

    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "Failed to save pick" });
    }
});

module.exports = router;

// NEW: Get a specific user's saved recommendations
router.get("/saved/:userId", async (req, res) => {
    try {
        const { userId } = req.params;
        
        // Join recommendations and catalog tables to get the full details of saved items.
        // Using DISTINCT prevents duplicates if the AI recommended the same item multiple times.
        const query = `
            SELECT DISTINCT c.title, c.type, c.description
            FROM recommendations r
            JOIN catalog c ON r.catalog_id = c.id
            WHERE r.user_id = $1
        `;
        
        const result = await pool.query(query, [userId]);
        res.json(result.rows);
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "Failed to fetch saved picks" });
    }
});

module.exports = router;