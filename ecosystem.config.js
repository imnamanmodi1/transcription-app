module.exports = {
  apps: [
    {
      name: "transcriptions-app",
      script: "app.py",
      interpreter: "python3",
      watch: true, // Optional: restarts on file changes
      env: {
        // Environment variables can be defined here if needed
      },
    },
  ],
};
