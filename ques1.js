const bcrypt = require('bcrypt');
const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());


const users = [];


app.post('/register', async (req, res) => {
    const { username, password } = req.body;
    
    
    const hashedPassword = await bcrypt.hash(password, 10); 
    
    
    users.push({ username, password: hashedPassword });
    res.send('User registered successfully');
});


app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    const user = users.find(u => u.username === username);
    
    if (!user) return res.status(400).send('User not found');
    
    
    const isMatch = await bcrypt.compare(password, user.password);
    if (isMatch) res.send('Login successful');
    else res.status(400).send('Invalid password');
});

app.listen(3000, () => console.log('Server running on port 3000'));
