import tomllib
import subprocess
import re
import shutil
import argparse
from pathlib import Path


def read_config(file_path):
    with open(file_path, "rb") as file:
        config = tomllib.load(file)
    return config


def check_pandoc():
    if not shutil.which("pandoc"):
        raise Exception("Pandoc is not installed")


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
    script_dir = Path(__file__).resolve().parent
    if csl_path is None:
        csl_path = Path(script_dir) / "anti-trafficking-review.csl"
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
    for match in FOOTNOTE_PATTERN.finditer(rtf_content):
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

        # the idea here is to look for the last curly brace that closes the footnote
        # since one is already opened at `footnote_start`, we can look for `{` and `}`
        # and if they are mismatched it means the `}` closes the `footnote_start` brace,
        # so it's the end of the footnote
        open_brace_pos = rtf_content.find("{", footnote_start + 1)
        close_brace_pos = rtf_content.find("}", footnote_start + 1)
        footnote_end = -1
        while open_brace_pos != -1 and close_brace_pos != -1:
            if open_brace_pos < close_brace_pos:
                open_brace_pos = rtf_content.find("{", close_brace_pos + 1)
                close_brace_pos = rtf_content.find("}", close_brace_pos + 1)
            else:
                footnote_end = close_brace_pos
                break
        if footnote_end == -1:
            print(
                "Warning: Could not find closing brace for footnote; this may means the footnote was malformed."
            )
        else:
            # now remove the first `\\par` before the closing brace
            start = rtf_content.rfind("\\par", footnote_start, footnote_end)
            rtf_content = rtf_content[:start] + rtf_content[close_brace_pos:]
    return rtf_content


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
        file_path = args.extract[0]
        regions_to_extract = extract_rtf_content(file_path)
        for file_name, rtf_content in regions_to_extract:
            print(f"Extracting {file_name}")
            out_file = output_dir / file_name
            out_file_rtf = out_file.with_suffix(".rtf")
            with open(out_file_rtf, "w") as file:
                file.write(rtf_content)
            input_content = convert(out_file_rtf, config["extract_filetype"])
            with open(out_file, "w") as file:
                file.write(input_content)
            out_file_rtf.unlink()
    else:
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

        with open(output_dir / official_template_path.name, "w") as file:
            file.write(official_template)


if __name__ == "__main__":
    main()
