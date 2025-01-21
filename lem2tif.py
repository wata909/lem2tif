import os
import re
import subprocess
from pathlib import Path
import csv
import zipfile

def process_lem_file(lem_file, csv_file, output_dir):
    # メタデータをCSVから読み込み
    metadata = {}
    with open(csv_file, 'r', encoding='shift_jis') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) >= 2:
                key = row[0].strip()
                value = row[1].strip()
                metadata[key] = value

    # デバッグ用に列名を表示
    print("CSV Metadata:", metadata)

    # メタデータの取得
    try:
        ncols = int(metadata['東西方向の点数'])
        nrows = int(metadata['南北方向の点数'])
        cellsize = float(metadata['東西方向のデータ間隔'])
        xllcorner = float(metadata['区画左下Y座標']) / 100.0  # cm単位をm単位に変換
        yllcorner = float(metadata['区画左下X座標']) / 100.0  # cm単位をm単位に変換
    except KeyError as e:
        print(f"Missing metadata in CSV file: {e}")
        return

    nodata_value = -99.9

    # 出力用ファイル名
    header_file = output_dir / f"{lem_file.stem}_header.asc"

    # ヘッダを書き込み
    with open(header_file, 'w', encoding='utf-8') as header:
        header.write(f"ncols         {ncols}\n")
        header.write(f"nrows         {nrows}\n")
        header.write(f"xllcorner     {xllcorner}\n")
        header.write(f"yllcorner     {yllcorner}\n")
        header.write(f"cellsize      {cellsize}\n")
        header.write(f"NODATA_value  {nodata_value}\n")

    # LEMデータ処理
    processed_data = []
    with open(lem_file, 'r', encoding='shift_jis') as infile:
        for line in infile:
            # ヘッダ部分を削除
            data_line = line[10:]
            # -9999, -1111を-999に置換
            data_line = re.sub(r"-9999", " -999", data_line)
            data_line = re.sub(r"-1111", " -999", data_line)
            # 10cm単位をm単位に変換
            values = [str(float(v) / 10.0) for v in data_line.split()]
            processed_data.append(" ".join(values))

    # 処理後のデータを書き込み
    with open(header_file, 'a', encoding='utf-8') as header:
        header.write("\n".join(processed_data))

    # GeoTIFFに変換
    output_tif = output_dir / f"{lem_file.stem}.tif"
    command = [
        "gdal_translate",
        "-of", "GTiff",
        "-a_srs", "EPSG:6677",
        "-a_nodata", str(nodata_value),
        str(header_file),
        str(output_tif)
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Converted {lem_file.name} to {output_tif.name}.")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {lem_file.name}: {e}")

def main():
    # 現在のディレクトリ
    current_dir = Path.cwd()
    # ZIPファイルを検索
    zip_files = list(current_dir.glob("*.zip"))

    if not zip_files:
        print("No .zip files found in the current directory.")
        return

    # 出力フォルダ
    output_dir = current_dir / "DEM"
    output_dir.mkdir(exist_ok=True)

    for zip_file in zip_files:
        # ZIPファイルを解凍
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            temp_dir = current_dir / zip_file.stem
            temp_dir.mkdir(exist_ok=True)
            zip_ref.extractall(temp_dir)

        # 解凍後のLEMとCSVファイルを処理
        lem_files = list(temp_dir.glob("*.lem"))
        for lem_file in lem_files:
            csv_file = lem_file.with_suffix('.csv')
            if not csv_file.exists():
                print(f"No corresponding CSV file for {lem_file.name}.")
                continue

            process_lem_file(lem_file, csv_file, output_dir)

        # 一時フォルダを削除
        for item in temp_dir.iterdir():
            item.unlink()
        temp_dir.rmdir()

if __name__ == "__main__":
    main()
