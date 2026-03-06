const express = require("express");
const User = require("../models/User");
const router = express.Router();

router.post("/register", async (req, res) => {
  const user = new User(req.body);
  await user.save();
  res.json(user);
});

router.get("/:id", async (req, res, next) => {
  try {
    const user = await User.findById(req.params.id);

    if (!user) {
      const error = new Error("User not found");
      error.status = 404;
      throw error;
    }

    res.json(user);

  } catch (err) {
    next(err);
  }
});

/*router.get("/", async (req, res) => {
  res.json(await User.find());
});*/

router.delete("/:id", async (req, res) => {
  const deletedUser = await User.findByIdAndDelete(req.params.id);
  res.json(deletedUser);
});

module.exports = router;