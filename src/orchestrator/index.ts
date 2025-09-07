import express from "express";
import multer from "multer";
import cors from "cors";
import { sleep } from "bun";
import JSZip from "jszip";

const app = express();

const port = 8080;
const DEBUG = process.env.VERBOSE === "true" || false;

const upload = multer({ storage: multer.memoryStorage() });
app.use(cors());

app.get("/", (req, res) => {
  console.log("Received request at /");
  res.send("Hello World!");
});

app.get("/health", (req, res) => {
  console.log("Received request at /health");
  // Test connectivity to other services

  let services = [
    { name: "Language Context", url: "http://language-context:8080/" },
    { name: "Codebase Context", url: "http://codebase-context:8080/" },
    {
      name: "Deployment Suggestion",
      url: "http://deployment-suggestion:8080/",
    },
    { name: "Terraform Generation", url: "http://generate-terraform:8080/" },
    // Add other services as needed
  ];

  let status: any = {};

  services.forEach(async (service) => {
    try {
      let response = await fetch(service.url || "", { method: "GET" });
      if (response.ok) {
        console.log(`* ${service.name} service is healthy.`);
        status[service.name] = "healthy";
      } else {
        console.error(
          `* ${service.name} service is down! Status: ${response.status}`
        );
        status[service.name] = "unhealthy";
      }
    } catch (error) {
      console.error(`* Error connecting to ${service.name} service:`, error);
    }
  });

  res.json(status);
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
  let languageContext = await languageContextExtract(instruction);

  // Send file to codebase context extraction service
  let codebaseContext = await codebaseContextExtract(file);

  while (!languageContext || !codebaseContext) {
    console.log("Waiting for both contexts to be available...");
    await sleep(1000);
  }
  // Send both contexts to suggestions service
  let suggestionsJSON: JSON | unknown = await suggestDeployment(
    languageContext,
    codebaseContext
  );

  while (!suggestionsJSON) {
    console.log("Waiting for suggestions to be available...");
    await sleep(1000);
  }

  // Send suggestion to Terraform generation service
  let terraformFiles = await generateTerraform(suggestionsJSON as JSON, file);

  while (!terraformFiles) {
    console.log("Waiting for Terraform files to be available...");
    await sleep(1000);
  }

  // Send back the Terraform files to the client
  res.json({ terraform_files: terraformFiles });

  if (DEBUG)
    console.log("* Final response: ", { terraform_files: terraformFiles });

  console.log("--------- Response sent successfully ---------");
});

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});

async function languageContextExtract(instruction: string) {
  console.log("❗ Sending instruction to language context service ---------");

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
  console.log("✅ Instruction sent successfully ---------");

  if (DEBUG)
    console.log("* Language context service responded: ", languageContext);

  return languageContext;
}

async function codebaseContextExtract(file: Express.Multer.File) {
  console.log(
    "❗ Sending file to codebase context extraction service ---------"
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
  console.log("✅ File sent successfully ---------");

  if (DEBUG)
    console.log(
      "* Codebase context extraction service responded: ",
      codebaseContext
    );
  return codebaseContext;
}

async function suggestDeployment(languageContext: any, codebaseContext: any) {
  console.log("--------- Sending data to suggestions service ---------");
  let reqBody = JSON.stringify({
    language_context: languageContext,
    codebase_context: codebaseContext,
  });

  let suggestions = await fetch(`${process.env.DEPLOYMENT_SUGGESTION_URL}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: reqBody,
  })
    .then((response) => response.json())
    .catch((error) => {
      console.error(
        "Error occurred while sending data to suggestions service:",
        error
      );
    });
  console.log("--------- Data sent successfully ---------");

  if (DEBUG) console.log("* Suggestions service responded: ", suggestions);
  return suggestions;
}

async function generateTerraform(
  suggestion: JSON,
  file: Express.Multer.File
): Promise<Buffer> {
  console.log(
    "❗ Sending suggestion to Terraform generation service ---------"
  );

  // 1️⃣ Send suggestion to Terraform service
  const response = await fetch(`${process.env.GENERATE_TERRAFORM_URL}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ suggestion }),
  });

  if (!response.ok) {
    throw new Error(`Terraform service returned ${response.status}`);
  }

  const terraformZipBuffer = Buffer.from(await response.arrayBuffer());

  console.log("✅ Received Terraform ZIP ---------");

  // 2️⃣ Load original repo ZIP and Terraform ZIP
  const repoZip = await JSZip.loadAsync(file.buffer);
  const tfZip = await JSZip.loadAsync(terraformZipBuffer);

  // 3️⃣ Merge Terraform files into repo ZIP
  tfZip.forEach((relativePath: any, fileEntry: any) => {
    if (!fileEntry.dir) {
      repoZip.file(relativePath, fileEntry.async("nodebuffer"));
    }
  });

  // 4️⃣ Generate updated ZIP buffer
  const updatedZipBuffer = await repoZip.generateAsync({ type: "nodebuffer" });

  console.log("✅ Merged Terraform files into repo ZIP ---------");
  return updatedZipBuffer;
}
