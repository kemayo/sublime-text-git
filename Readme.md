# Sublime Text 3 plugin: git (Fork)

This fork of [Git](https://github.com/kemayo/sublime-git) for Sublime Text supports the usual features and adds the following:

	- Tag support (Create, Delete, Checkout)
	- Cherry Pick
	- Progress bar/ Spinner while caling a command
	- Checkout any commit you want
	- GitX support on OS X
	- Bugfixes

## Installation

### Using Package Control:

Using Package Control, add custom repostory `https://github.com/Chris---/SublimeText-Git` and add a name_map to your settings like this.

	"package_name_map":
	{
		"SublimeText-Git": "Git"
	}

* Bring up the Command Palette (Command+Shift+P on OS X, Control+Shift+P on Linux/Windows).
* Select Package Control: Install Package.
* Select Git to install as usual.

### Not using Package Control:

* Save files to the `Packages/Git` directory, then relaunch Sublime:
  * Linux: `~/.config/sublime-text-2|3/Packages/Git`
  * Mac: `~/Library/Application Support/Sublime Text 2|3/Packages/Git`
  * Windows: `%APPDATA%/Sublime Text 2|3/Packages/Git`

For more information about what's supported, check the original wiki.