import pandas as pd
import one_cell_imu_data_extraction as one
import os
import time

if __name__ == '__main__':
    cell_df = pd.DataFrame()

    one_cell_port = one.get_cell_com_port(1155)
    print(one_cell_port)
    print(os.getcwd())
    cell_df = one.read_hw_info(one_cell_port[0])
    print("Check valid data = ", cell_df['valid'].values[0])

    if cell_df['valid'].values[0]:
        print("#0", cell_df['file_name'].values[0])

        name_first_split = cell_df['file_name'].values[0].split("-")
        name_second_split = name_first_split[len(name_first_split) - 1].split("_")
        print(name_first_split)
        print(name_second_split)

        hw_version = name_first_split[1]
        fw_version = name_second_split[1]
        print(hw_version, fw_version)
        # Check .ftg format applied
        if hw_version >= "4A" and float(fw_version) >= 12.0:
            print(".ftg format file write")
            filepath_ftg = os.getcwd() + "/" + cell_df['file_name'].values[0] + ".ftg"
            one.read_and_save_gps_data(filepath_ftg, cell_df)
        else:
            print("Old FW .gp/.im file write")
            filepath_gp = os.getcwd() + "/" + cell_df['file_name'].values[0] + ".gp"
            filepath_im = os.getcwd() + "/" + cell_df['file_name'].values[0] + ".im"
            print(filepath_gp)
            one.read_and_save_gps_data(filepath_gp, cell_df)
            one.read_and_save_imu_data(filepath_im, cell_df)

    # cell RAM variable not reset when you erase nand flash
    # you need manual reset
    one.erase_cell_nand_flash(one_cell_port, cell_df)

    # del cell_df

# b'\xca`\x05\x11\x03Q\x00\x00\xec'
# 0xca60051103510000ec