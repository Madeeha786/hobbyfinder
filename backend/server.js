const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
require("dotenv").config();

const userRoutes = require("./routes/users");
const catalogRoutes = require("./routes/catalog");
const aiRoutes = require("./routes/ai");

const app = express();   // ✅ CREATE APP FIRST

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("HobbyFinder backend is running");
});

mongoose.connect("mongodb://127.0.0.1:27017/hobbyfinder")
.then(() => console.log("MongoDB Connected"))
.catch(err => console.log(err));

// routes
app.use("/api/users", userRoutes);
app.use("/api/catalog", catalogRoutes);
app.use("/api/ai", aiRoutes);

app.listen(5000, () => {
  console.log("Backend running on port 5000");
});
