# MSCA PF Templates Script

This script is designed to assist with the preparation of Marie Skłodowska-Curie Actions
(MSCA) Postdoctoral Fellowship (PF) templates. It automates the process of converting
files to RTF format, inserting them into an official template, and extracting them back
to the original format. This allows you to use LaTeX of Markdown to write your proposal,
with full support for BibTeX.

You can use this script to convert these files into RTF format, insert them into the official MSCA PF template, and then extract them back into LaTeX format after receiving feedback from your advisor.

For an example of rendered output, see the [this](output/output.pdf) file.

## TL;DR

1. Name your files as the section number (e.g., `1.1.file1.tex`).
2. Run `python rtfcompile.py` to compile the files.
3. Adjust some minor formatting (image/text/table alignment and footnotes)
4. Send the RTF file to your advisor.
5. Run `python rtfcompile.py --extract file_modified_by_supervisor.rtf` to extract the files back to LaTeX.

## Installation

Clone the repository from GitHub or download the zip file and extract it:

```bash
git clone https://github.com/username/repository.git
```

### Windows

I recommend using the Windows Subsystem for Linux (WSL) to run the script on Windows. You can install WSL by following the instructions [here](https://docs.microsoft.com/en-us/windows/wsl/install).

However, you can also run the script on Windows natively (not tested):

1. Install Python 3.11 or higher. You can download it from the [official Python website](https://www.python.org/downloads/).
2. Install Pandoc. You can download it from the [official Pandoc website](https://pandoc.org/installing.html).

### Linux/Mac

1. Install Python 3.11 or higher. You can do this using a package manager like `apt` for Ubuntu or `brew` for MacOS.

2. Install Pandoc. On Ubuntu, you can use `apt`:

```bash
sudo apt-get install pandoc
```

On MacOS, you can use `brew`:

```bash
brew install pandoc
```

## Configuration

The script uses a `config.toml` file for configuration. Use the provided `config.toml`
file as a template and modify it as needed. Documentation for the configuration options is provided in the file.

## Usage

To use the script, run it from the command line:

```bash
python rtfcompile.py
```

This will convert the files in the `input_dir` directory to RTF format, insert them into the official template, and save the result in the `output_dir` directory.

Files are inserted in the order they are sorted alphabetically, so make sure to name
them accordingly. It's advisable to use the section number as a prefix (e.g., `1.1.file1.tex`).

Citations will be saved as plain text footnotes when using the default citation style. You can use a different citation style by modifying the `citation_style` option in the `config.toml` file. You can find a databse of citation styles [here](https://www.zotero.org/styles).

When you want to extract the files back to the original format, for instance after supervisor revision, use the `--extract` option:

```bash
python rtfcompile.py --extract file_modified_by_supervisor.rtf
```

The extracted files will be saved in the `output_dir` directory.

Note that citations will be saved as plain text in the extracted source.

## Directory Structure

An example directory structure is shown below:

```
.
├── config.toml
├── input_dir
│   ├── 1.1.file1.tex
│   ├── 1.2.file2.tex
│   ├── 2.1.file2.tex
│   └── ...
├── image.png
├── bibliography.bib
├── other_files
│   ├── other_bibliography.bib
│   ├── other_image.png
│   └── ...
├── output_dir
│   └── ...
└── official_template.rtf
```

- `config.toml`: The configuration file.
- `input_dir`: The directory containing the input files. This can be any file supported
  by Pandoc (e.g., LaTeX, Markdown). Files should be alphabetically sortable in the same
  order as they should be inserted. It's advisable to keep files named with the section
  number (e.g., `1.1.file1.tex`, or `11file1.tex`).
- `image.png`: An image file that will be inserted into the official template.
- `bibliography.bib`: A bibliography file.
- `other_files`: A directory containing additional files that will be inserted into the
  compiled document. It should be added to the `resource_paths` option in the
  configuration.
- `output_dir`: The directory where the output files will be saved.
- `official_template.rtf`: The official template file.

## Known Issues

### Scaling of Images and Floats

Since the system uses fragments of LaTeX, Pandoc is unaware of page sizes. Consequently,
scaling of images and floats won't work as expected. You should use absolute values,
instead.

Since the standard format is A4, which is 21 cm wide, and the borders are 2.54 cm wide
(2024 template), the text width is 21 - 2 \* 2.54 = 15.92 cm. You can use this value in
place of `\textwidth`.

For example, to scale an image to 50% of the text width, use:

```latex
\includegraphics[width=7.96cm]{image.png}
```

### Text Alignment

Unfortunately, text alignment is not supported in Pandoc for RTF. This means you cannot
center floats, nor text or math in the source code.
You should manually adjust the alignment in the RTF document.

### Footnotes

Footnotes are supported but you may want to reformat them because empty paragraphs are
introduced and the font size is slightly not always uniform.

### Extraction

The extraction process -- i.e. from RTF to latex or markdown -- is not perfect. And it
is recommended to manually copy and post from the extracteed files into the original
sources.

# Credits

Federico Simonetta, https://federicosimonetta.eu.org
