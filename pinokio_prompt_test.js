module.exports = {
  run: [
    { method: "shell.run", params: { venv: "env", path: "F:/code/video-studio/app", env: { PYTHONUNBUFFERED: "1", PYTHONIOENCODING: "utf-8" },
        message: ["python _step_test.py > F:/code/video-studio/_tests/step_test/run.log 2>&1"] } }
  ]
}
