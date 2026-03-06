const mongoose = require("mongoose");

const activitySchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "User",
    required: true
  },

  hobby: {
    type: String,
    required: true
  },

  progress: {
    type: Number,
    default: 0
  },

  completed: {
    type: Boolean,
    default: false
  },

  updatedAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model("Activity", activitySchema);