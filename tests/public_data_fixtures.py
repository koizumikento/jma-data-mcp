"""Synthetic examples of JMA's published file formats."""

from io import BytesIO
from zipfile import ZipFile

NORMALS_PATH = "/stats/data/mdrr/normal/2020/data/normal_amedas_monthly.zip"
ANOMALIES_PATH = "/cpdinfo/temp/list/csv/an_jpn.csv"
WARNING_PATH = "/developer/xml/feed/extra_l.xml"


def public_files() -> dict[str, bytes]:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        months = ["    54,8", "     0,0", "    -7,7", *["     0,8"] * 9]
        archive.writestr(
            "monthly/area44/nml_amd_m_44132.csv",
            "21,44132,0500,30,1991,2020," + ",".join([*months, "   158,8"]),
        )
    entries = []
    for code, hour, office in [("VPWW53", "01", "気象庁"), ("VPWW55", "03", "気象庁"), ("VTSE41", "02", "札幌管区気象台")]:
        entries.append(f"""<entry>
            <title>気象警報・注意報</title>
            <updated>2026-10-10T{hour}:00:00Z</updated>
            <author><name>{office}</name></author>
            <link href="https://www.data.jma.go.jp/developer/xml/data/20261010{hour}0000_0_{code}_130000.xml" />
            <content type="text">電文の概要</content>
          </entry>""")
    feed = '<feed xmlns="http://www.w3.org/2005/Atom"><updated>2026-10-10T04:00:00Z</updated>'
    return {
        NORMALS_PATH: buffer.getvalue(),
        ANOMALIES_PATH: "年,偏差\r\n1898,-1.03\r\n2025,+1.23\r\n".encode("shift_jis"),
        WARNING_PATH: (feed + "".join(entries) + "</feed>").encode("utf-8"),
    }
