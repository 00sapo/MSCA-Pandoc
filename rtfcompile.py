import argparse
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

import tomllib


def read_config(file_path):
    with open(file_path, "rb") as file:
        config = tomllib.load(file)
    return config


def check_pandoc():
    if not shutil.which("pandoc"):
        raise Exception("Pandoc is not installed")


def check_libreoffice():
    """Check if LibreOffice is installed on the system"""
    if platform.system() == "Windows":
        # Paths where LibreOffice is typically installed on Windows
        paths = [
            "C:\\Program Files\\LibreOffice",
            "C:\\Program Files (x86)\\LibreOffice",
        ]

        for path in paths:
            if os.path.exists(path):
                return [path]

    elif platform.system() in ["Linux", "Darwin"]:
        # Check if LibreOffice is installed as a system package or as a Flatpak
        if shutil.which("libreoffice") or shutil.which("soffice"):
            return ["libreoffice"]

        # Check if LibreOffice is installed as a Flatpak
        try:
            result = subprocess.run(
                ["flatpak", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            if "org.libreoffice.LibreOffice" in result.stdout.decode("utf-8"):
                return ["flatpak", "run", "org.libreoffice.LibreOffice"]
        except FileNotFoundError:
            pass

    return None


def validate_files(file_paths: Path):
    for file_path in file_paths:
        file_name = file_path.name
        if not re.match(r"\d{2}", file_name.replace(".", "")):
            print(f"Warning: {file_name} does not start with a two-digit number")


def sort_files(file_paths):
    return sorted(file_paths, key=lambda x: x.name)


def find_string(content, string):
    start_index = content.find(string)
    if start_index != -1:
        start_brace = content.rfind("{", 0, start_index)
        end_brace = content.find("}", start_index)
        if start_brace != -1 and end_brace != -1:
            return start_brace, end_brace + 1
    return None


def convert(
    file_path,
    output_type,
    csl_path=None,
    resource_paths=None,
    suppress_bibliography=False,
    footnote_size=10,
):
    if csl_path is None:
        raise ValueError("citation_style must be provided in the config")
    command = [
        "pandoc",
        file_path,
        "--citeproc",
        f"--csl={csl_path}",
        f"--to={output_type}",
        f"--metadata=suppress-bibliography:{suppress_bibliography}",
    ]
    if resource_paths is not None:
        resource_path = ".:" + resource_paths
        command.append(f"--resource-path={resource_path}")
    command = [str(x) for x in command]
    print("Running pandoc: " + " ".join(command))
    result = subprocess.run(command, stdout=subprocess.PIPE)
    rtf_content = result.stdout.decode()
    rtf_content = fix_footnotes(rtf_content, footnote_size)
    return rtf_content


def prepend_append_rtf(rtf_content, file_name):
    prepend = "{\\comment tex2rtf/from: " + file_name + "}\n"
    append = "\n{\\comment tex2rtf/to: " + file_name + "}"
    return prepend + rtf_content + append


def extract_rtf_content(file_path):
    with open(file_path, "r") as file:
        content = file.read()
    matches = re.findall(
        r"{\\comment tex2rtf/from: (.*?)}(.*?){\\comment tex2rtf/to: \1}",
        content,
        re.DOTALL,
    )
    return [(match[0], match[1].strip()) for match in matches]


FOOTNOTE_PATTERN = re.compile(r"\\footnote")


def fix_footnotes(rtf_content, footnote_size):
    """Looks for `\\footnote` and removes the ending `\\par` and sets font size for the footnote (in half points)"""
    footnote_size = int(footnote_size * 2)
    # for each footnote
    # find next match
    start_match_search = 0
    while True:
        match = FOOTNOTE_PATTERN.search(rtf_content, start_match_search)
        if match is None:
            break
        # find the next `\\chftn` and insert a `\\fsxx` before it
        # this is for the footnote number
        start = match.start()
        end = rtf_content.find("\\chftn", start)
        if end == -1:
            print(
                "Warning: Could not find `\\chftn` after `\\footnote`; this may means the footnote was malformed."
            )
        rtf_content = rtf_content[:end] + f"\\fs{footnote_size}" + rtf_content[end:]
        # now look for the first `{` after the `\\chftn` and insert another `\\fsxx`
        # after the `\\pard` after that
        # this is for the footnote text
        start = end
        footnote_start = rtf_content.find("{", start)
        end = rtf_content.find("\\pard", footnote_start + 1) + 5
        rtf_content = rtf_content[:end] + f"\\fs{footnote_size}" + rtf_content[end:]

        # loop char by char until we find the closing `}`
        open_braces = 1
        close_braces = 0
        for i in range(end, len(rtf_content)):
            if rtf_content[i] == "{":
                open_braces += 1
            elif rtf_content[i] == "}":
                close_braces += 1
            if open_braces == close_braces:
                break
        # now we are at the closing `}`
        # remove the `\\par` before it
        start = rtf_content.rfind("\\par", start, i)
        rtf_content = rtf_content[:start] + rtf_content[start + 4 :]
        start_match_search = i - 4

    return rtf_content


def extraction(args, config, output_dir) -> None:
    file_path = args.extract[0]
    regions_to_extract = extract_rtf_content(file_path)
    for file_name, rtf_content in regions_to_extract:
        out_file = output_dir / file_name
        out_file_rtf = out_file.with_suffix(".rtf")
        with open(out_file_rtf, "w") as file:
            file.write(rtf_content)
        input_content = convert(out_file_rtf, config["extract_filetype"])
        with open(out_file, "w") as file:
            file.write(input_content)
        out_file_rtf.unlink()


def compile(config, input_dir, official_template_path, output_dir):
    with open(config["official_template"], "r") as file:
        official_template = file.read()

    input_files = list(input_dir.glob("*"))
    validate_files(input_files)
    sorted_files = sort_files(input_files)
    for file_path in sorted_files:
        print(f"Converting {file_path.name}")
        occurrence = find_string(official_template, config["string"])
        if occurrence is None:
            raise RuntimeError(
                f'Could not find string `{config["string"]}` in {config["official_template"]}'
            )
        rtf_content = convert(
            file_path,
            "rtf",
            config.get("citation_style"),
            config.get("resource_paths"),
            config["suppress_bibliography"],
            config.get("footnote_size"),
        )
        rtf_content = prepend_append_rtf(rtf_content, file_path.name)
        official_template = (
            official_template[: occurrence[0]]
            + rtf_content
            + official_template[occurrence[1] :]
        )

    output_rtf_path = output_dir / official_template_path.name
    with open(output_rtf_path, "w") as file:
        file.write(official_template)

    libreoffice = check_libreoffice()
    if libreoffice is not None:
        # convert to pdf
        subprocess.run(
            libreoffice
            + [
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                output_rtf_path.with_suffix(".pdf"),
            ]
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e", "--extract", nargs=1, metavar="file", help="RTF file to extract from"
    )
    args = parser.parse_args()

    config = read_config("config.toml")
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(exist_ok=True, parents=True)
    input_dir = Path(config["input_dir"])
    official_template_path = Path(config["official_template"])

    check_pandoc()

    if args.extract:
        extraction(args, config, output_dir)
    else:
        compile(config, input_dir, official_template_path, output_dir)


if __name__ == "__main__":
    main()
