import express from "express";
import multer from "multer";
import cors from "cors";

const app = express();

const port = 8080;
const DEBUG = process.env.VERBOSE === "true" || false;

const upload = multer({ storage: multer.memoryStorage() });
app.use(cors());

app.get("/", (req, res) => {
  console.log("Received request at /");
  res.send("Hello World!");
});

app.post("/upload", upload.single("repo_zip"), async (req, res) => {
  console.log("--------- Received request at /upload ---------");

  const file = req.file;
  const instruction = req.body.instruction;

  if (!file) {
    return res.status(400).json({ error: "No file uploaded." });
  }

  console.log("* File details:", file);
  console.log("* Instruction:", instruction);


  // Send instruction to language model service
  let languageContext = languageContextExtract(instruction);

  // Send file to codebase context extraction service
  let codebaseContext = codebaseContextExtract(file);

  console.log("OUTPUT:", languageContext, codebaseContext);
  res.json({ languageContext, codebaseContext });
});

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});

async function languageContextExtract(instruction: string) {
  console.log(
    "--------- Sending instruction to language context service ---------"
  );

  let languageContext = await fetch(`${process.env.LANGUAGE_CONTEXT_URL}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ instruction }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(
          `Language context service responded with status ${response.status}`
        );
      }
      return response.json();
    })
    .catch((error) => {
      console.error(
        "Error occurred while sending instruction to language context service:",
        error
      );
    });
  console.log("--------- Instruction sent successfully ---------");

  if (DEBUG)
    console.log("* Language context service responded: ", languageContext);

  return languageContext;
}

async function codebaseContextExtract(file: Express.Multer.File) {
  console.log(
    "--------- Sending file to codebase context extraction service ---------"
  );
  let codebaseContext = await fetch(`${process.env.CODEBASE_CONTEXT_URL}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/zip",
      "X-Filename": file.originalname,
    },
    body: file.buffer,
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(
          `Codebase context extraction service responded with status ${response.status}`
        );
      }

      return response.json();
    })
    .catch((error) => {
      console.error(
        "Error occurred while sending file to codebase context extraction service:",
        error
      );
    });
  console.log("--------- File sent successfully ---------");

  if (DEBUG)
    console.log(
      "* Codebase context extraction service responded: ",
      codebaseContext
    );
  return codebaseContext;
}

