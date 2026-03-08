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

// NEW: Get interests by User ID
router.get("/:userId", async (req, res) => {
    try {
        const interest = await Interest.findOne({ user_id: req.params.userId });
        if (!interest) {
            return res.status(404).json({ message: "No interests found for this user" });
        }
        res.json(interest);
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "Failed to fetch profile interests" });
    }
});

module.exports = router;