# Contributing

## Development Setup

The easiest way to get all the required libraries installed for Gremlin development is via a virtual environment managed by [Poetry](https://python-poetry.org) [1]. Throughout this the assumption is that [VS Code](https://code.visualstudio.com/) [2] is used and the appropriate Python plugins are installed.

### Installing Poetry

Abbreviated instructions from the [official documentation](https://python-poetry.org/docs/#installing-with-the-official-installer)

- Install a Gremlin compatible version of Python, such as 3.12.x
- Open a new Terminal / Powershell instance
- Run the command
  ```powershell
  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
  ```

- Add the poetry executable to your PATH setting
  ```powershell
  [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Users\Lionel\AppData\Roaming\Python\Scripts", "User")
  ```

- Launch a new Terminal / Powershell instance and check if poetry can be found by running
  ````powershell
  poetry --version
  ````

- Add the Poetry plugin (`zeshuaro.vscode-python-poetry`) to VS Code

- Create a virtual environment and install required packages by running the `Poetry install packages` command (`Ctrl + Shift + P`) in VS Code

- Restart VS Code for the new environment to be picked up

- Select the newly created Poetry virtual environment as the project's interpreter



## Coding Style





## Code-Base Structure





## References

[1] https://python-poetry.org

[2] https://code.visualstudio.com/