const express = require("express");
const router = express.Router();
const Interest = require("../models/Interest");

router.post("/", async (req,res) => {

try{

const interest = new Interest({
user_id: req.body.user_id,
books: req.body.books,
movies: req.body.movies,
songs: req.body.songs
});

await interest.save();

res.json({
message:"Interests saved",
data:interest
});

}catch(err){

console.error(err);
res.status(500).json({error:"Failed to save interests"});

}

});

module.exports = router;