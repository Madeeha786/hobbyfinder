const mongoose = require("mongoose");

const interestSchema = new mongoose.Schema({

 user_id: {
   type: mongoose.Schema.Types.ObjectId,
   ref: "User"
 },

 books: [String],
 movies: [String],
 songs: [String]

});

module.exports = mongoose.model("Interest", interestSchema);