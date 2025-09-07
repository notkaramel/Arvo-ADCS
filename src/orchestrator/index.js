import express from 'express'
const app = express()
const port = 8080

app.get('/', (req, res) => {
  console.log('Received request at /')
  res.send('Hello World!')
})

app.post('/upload', async (req, res) => {
  console.log('Received request at /upload')
})

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`)
})
