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

router.post("/recommend", async (req, res) => {

try{

const interests = req.body.interests;
const user_id = req.body.user_id;

/* Call Flask AI */

const response = await axios.post("http://127.0.0.1:8000/recommend", interests);

const recommendations = response.data.recommendations;

/* Store recommendations in PostgreSQL */

for (const item of recommendations) {

const catalog = await pool.query(
"SELECT id FROM catalog WHERE title = $1",
[item.title]
);

if(catalog.rows.length > 0){

const catalog_id = catalog.rows[0].id;

await pool.query(
"INSERT INTO recommendations (user_id, catalog_id) VALUES ($1,$2)",
[user_id, catalog_id]
);

}

}

res.json(recommendations);

}catch(err){

console.error(err);
res.status(500).json({error:"AI recommendation failed"});

}

});

module.exports = router;