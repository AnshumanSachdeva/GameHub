const jwt = require('jsonwebtoken');
const SECRET_KEY = 'your_secret_key'; 


app.post('/login-jwt', async (req, res) => {
    const { username, password } = req.body;
    const user = users.find(u => u.username === username);
    
    if (!user) return res.status(400).send('User not found');
    
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(400).send('Invalid password');
    
    
    const token = jwt.sign(
        { username: user.username, role: user.role || 'user' }, 
        SECRET_KEY,
        { expiresIn: '15m' } 
    );

    res.json({ message: 'Login successful', token });
});


app.get('/dashboard', (req, res) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) return res.status(401).send('Access denied');

    try {
        const decoded = jwt.verify(token, SECRET_KEY);
        res.send(`Welcome ${decoded.username}, your role is ${decoded.role}`);
    } catch (err) {
        res.status(403).send('Invalid or expired token');
    }
});
