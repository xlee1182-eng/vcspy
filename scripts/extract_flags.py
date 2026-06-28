"""Constants.java 에서 FLAG_* 배열을 추출해 app/tcp/flags.py 생성."""
import re
import pathlib

src = pathlib.Path(
    "D:/Projects/vcsPython/decompiled/vcs_260611/com/ygcloud/ygvcs/utils/Constants.java"
).read_text(encoding="utf-8")

out = [
    '"""원본 com.ygcloud.ygvcs.utils.Constants 의 FLAG_* 배열 (자동추출).',
    "",
    "AGV 응답 플래그 인덱스 → 사람이 읽을 메시지. is_0xff_or_0x00 에서 사용.",
    '"""',
    "",
]


def decode(s: str) -> str:
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)


arr_re = re.compile(r"public static final String\[\] (FLAG_\w+) = new String\[\]\{([^}]*)\};")
str_re = re.compile(r'"((?:[^"\\]|\\.)*)"')

count = 0
for m in arr_re.finditer(src):
    name, body = m.group(1), m.group(2)
    items = [decode(x) for x in str_re.findall(body)]
    out.append(f"{name} = {items!r}")
    count += 1

pathlib.Path("app/tcp/flags.py").write_text("\n".join(out) + "\n", encoding="utf-8")
print("추출된 FLAG 배열:", count)
