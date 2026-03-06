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

router.get("/", async (req, res) => {
  const result = await pool.query("SELECT * FROM catalog");
  res.json(result.rows);
});

module.exports = router;