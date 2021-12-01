import serial.tools.list_ports
import serial
from time import time
import pandas as pd
import os
from time import sleep

BAUDRATE = 230400
CELL_IMU_CAL_RESP_SIZE = 128
CELL_GPSERR_IMUERR_COUNT = "AC C0 01 25 48"
SYSCOMMAND_UPLOAD_TOTAL_GPS_AND_IMU_SIZE = "AC C0 01 11 7C"
SYSCOMMAND_UPLOAD_TOTAL_GPS_AND_IMU_RESP_SIZE = 9
SYSCOMMAND_HW_INFORMATION = "AC C0 01 10 7D"
SYSCOMMAND_HW_INFORMATION_RESP_SIZE = 23
SYSCMD_GET_BADBLOCK_NUMBER = "AC C0 01 D6 BB"
SYSCMD_GET_BADBLOCK_NUMBER_RESP_SIZE = 6
SYSCOMMAND_SET_READ_IMU_CAL = "AC C0 01 24 49"
SYSCOMMAND_OLD_UPLOAD_IMU_DATA = "AC C0 01 E1 8C"
SYSCOMMAND_OLD_UPLOAD_GPS_DATA = "AC C0 02 E0 00 8E"
SYSCOMMAND_OLD_UPLOAD_TEMP_DATA = "AC C0 01 E4 89"
CELL_GPS_IMU_READ_CHUCK_SIZE = 2048
SYSCOMMAND_ERASE_NAND_FLASH = "AC C0 01 15 78"
SYSCOMMAND_ERASE_NAND_FLASH_RESP_SIZE = 8
IMU_ERR_STR = "IMUERR"
GPS_ERR_STR = "GPSERR"
GPS_END_STR = "GPSEND"
file_path = "./cell data"
frame_to_time_scaler = 1 / 6000

# Add new command - Renewal data manager
DATA_READ_STOP = "AC C0 01 F3 9E"

DEBUG_LOG_PRINT = 1


def to_float(x):
    try:
        return float(x)
    except:
        return 0.


def get_cell_com_port(cell_vendor_id):
    cell_port_name = ''
    cell_port_list = []
    for port in serial.tools.list_ports.comports():
        if port.vid == cell_vendor_id:
            cell_port_name = port.device
            cell_port_list.append(cell_port_name)
    if cell_port_name == '':
        print("Please make sure Cell plug into docking")

    return cell_port_list


def check_cell_has_data(usart):
    # print("check cell has data")
    hex_buf = bytes.fromhex(SYSCOMMAND_UPLOAD_TOTAL_GPS_AND_IMU_SIZE)
    usart.write(hex_buf)

    in_bin = usart.read(SYSCOMMAND_UPLOAD_TOTAL_GPS_AND_IMU_RESP_SIZE)
    print("#2")
    print(in_bin)
    in_hex = hex(int.from_bytes(in_bin, byteorder='big'))
    print(in_hex)

    sum_data = (int(in_hex[10], 16) + int(in_hex[11], 16) + int(in_hex[12], 16) + int(in_hex[13], 16))

    gps_page_size = str(in_hex[10]) + str(in_hex[11]) + str(in_hex[12]) + str(in_hex[13])
    imu_page_size = str(in_hex[14]) + str(in_hex[15]) + str(in_hex[16]) + str(in_hex[17])
    # print(gps_page_size)
    gps_page_size = int(gps_page_size, 16)
    # print(imu_page_size)
    imu_page_size= int(imu_page_size, 16)

    return sum_data, gps_page_size, imu_page_size


def hex_to_ascii(hex_name):
    bytes_object = bytes.fromhex(hex_name)
    ascii_name = bytes_object.decode("ASCII")
    return ascii_name


def get_hw_info(usart):
    # print("get hw info")
    retry_cnt = 0
    hex_buf = bytes.fromhex(SYSCOMMAND_HW_INFORMATION)
    while retry_cnt < 3:
        # try:
        # print("try here")
        usart.write(hex_buf)
        in_bin = usart.read(SYSCOMMAND_HW_INFORMATION_RESP_SIZE)
        # print("Print length of in_bin", len(in_bin))
        if len(in_bin) != SYSCOMMAND_HW_INFORMATION_RESP_SIZE:
            # print("Retry hw info")
            usart.write(hex_buf)
            in_bin = usart.read(SYSCOMMAND_HW_INFORMATION_RESP_SIZE)
            retry_cnt += 1
        else:
            # print("Get cell hw info")
            break
        # except usart.SerialTimeoutException:
        #     print("Didn't get any information from cell")
        #     retry_cnt += 1
    in_hex = hex(int.from_bytes(in_bin, byteorder='big'))

    # print("Printed all hw info : ", in_hex)

    serial_number = int(in_hex[10:14], 16)
    # firm_ver = str(int(in_hex[14:18], 16))
    major_firm_ver = str(int(in_hex[14:16], 16))
    minor_firm_ver = str(int(in_hex[16:18], 16))
    product_id = in_hex[18:22]
    version_id = in_hex[22:26]
    product_version = in_hex[30:34]

    product_id_ascii_string = hex_to_ascii(product_id)
    version_id_ascii_string = hex_to_ascii(version_id)
    product_version_ascii_string = hex_to_ascii(product_version)

    serial_number = str(serial_number)
    firm_ver = str(major_firm_ver) + "." + str(minor_firm_ver)

    return product_id_ascii_string, version_id_ascii_string, product_version_ascii_string, serial_number, firm_ver


def get_cell_badblock_number(usart):
    hex_buf = bytes.fromhex(SYSCMD_GET_BADBLOCK_NUMBER)
    usart.write(hex_buf)
    in_bin = usart.read(SYSCMD_GET_BADBLOCK_NUMBER_RESP_SIZE)
    in_hex = hex(int.from_bytes(in_bin, byteorder='big'))
    bad_sector_num = in_hex[13:15]
    # print("bad sector", in_hex)
    # print("TRUE bad sector", in_hex[13:15])

    return bad_sector_num


def get_time_when_file_create():
    print(time())
    unix_time = int(time())
    # print(unix_time)

    return unix_time


def read_hw_info(one_cell_port):
    cell_df = pd.DataFrame()

    # for current_cell_port in port_list:
    try:
        usart = serial.Serial(one_cell_port, BAUDRATE, timeout=3)
    except (OSError, serial.SerialException):
        print("THIS cell port not read cell info", one_cell_port)
        pass

    print("he", one_cell_port)

    sum_data, gps_page_size, imu_page_size = check_cell_has_data(usart)
    product_id, version_id, product_version, production_number, firm_ver = get_hw_info(usart)

    print(product_id, version_id, product_version, production_number, firm_ver)
    print(sum_data, gps_page_size, imu_page_size)

    if sum_data:
        valid = True
        bad_sector_num = get_cell_badblock_number(usart)
        unix_time = get_time_when_file_create()
    else:
        valid = False
        bad_sector_num = 0
        unix_time = 0

    serial_number = "{}{}-{}-{}".format(product_id, version_id, product_version, production_number)
    file_name = "{}_{}_0_{}_{}".format(serial_number, firm_ver, unix_time, bad_sector_num) if valid else ''

    cell_dict = {
        "port": one_cell_port,
        "serial_number": serial_number,
        "product_id": product_id,
        "version_id": version_id,
        "product_version": product_version,
        "production_number": production_number,
        "firmware_version": firm_ver,
        "valid": valid,
        "data_size": sum_data,
        "gps_page_size": gps_page_size,
        "imu_page_size": imu_page_size,
        "bad_sector_count": bad_sector_num,
        "unix_time": unix_time,
        "file_name": file_name
    }
    dtypes = {
        "port": str,
        "serial_number": str,
        "product_id": str,
        "version_id": str,
        "product_version": str,
        "production_number": str,
        "firmware_version": str,
        "valid": bool,
        "data_size": int,
        "gps_page_size": int,
        "imu_page_size": int,
        "bad_sector_count": int,
        "unix_time": int,
        "file_name": str
    }

    cell_df = cell_df.append(cell_dict, ignore_index=True)
    cell_df = cell_df.astype(dtypes)

    return cell_df


def progress_bar(total_size, current_size):
    for i in range(100):
        msg = '\r진행률 %d%%' %( i + 1)
        print(msg, end='')


def filename_without_extension(filepath):
    return os.path.basename(filepath).replace('.' + filepath.split('.')[-1], '')


def change_filename_include_error_count(filepath, error_count):
    old_filename = os.path.basename(filepath)
    front_filename = old_filename.split('_')[0] + '_' + old_filename.split('_')[1] + '_'
    backend_filename = '_' + old_filename.split('_')[3] + '_' + old_filename.split('_')[4]
    new_filename = front_filename + str(error_count) + backend_filename
    new_file_path = os.path.join(os.path.dirname(filepath), new_filename)
    # time.sleep(1)
    os.rename(filepath, new_file_path)

    return new_file_path


def read_and_save_gps_data(filepath, cell_df, callback=True):
    read_error_msg = ''

    filename_without_ext = filename_without_extension(filepath)
    print(filename_without_ext)
    port = cell_df.loc[cell_df['file_name'] == filename_without_ext, 'port'].values[0]
    gps_page_size = cell_df.loc[cell_df['file_name'] == filename_without_ext, 'gps_page_size'].values[0]
    serial_number = cell_df.loc[cell_df['file_name'] == filename_without_ext, 'serial_number'].values[0]

    if DEBUG_LOG_PRINT:
        print(filepath + port + " Start reading GPS data")
        print("GP file page size = ", gps_page_size)
    read_succeed = True
    gps_data_chuck_validation_cnt = 0
    start_string_find_flag = 1
    if DEBUG_LOG_PRINT:
        print(filepath + port + " Start reading GPS data")

    # start_time = time.time()
    try:
        with serial.Serial(port, BAUDRATE, timeout=0.1) as ser, \
                open(filepath, mode='w+b') as f:

            gps = bytes.fromhex(SYSCOMMAND_OLD_UPLOAD_GPS_DATA)
            ser.write(gps)

            # while start_string_find_flag:
            #     data = ser.read(CELL_GPS_IMU_READ_CHUCK_SIZE)
            #     str_data = str(data)
            #     if (str_data.find('start')) != -1:
            #         f.write(data[6:])
            #         start_string_find_flag = 0
            #         break

            gps_data_reading_end_flag = 1
            gps_error_str_delete_flag = 0

            while gps_data_reading_end_flag:
                data = ser.read(CELL_GPS_IMU_READ_CHUCK_SIZE)
                str_data = str(data)

                msg = '\rGPS 진행률 %d%%\r' % (100 * gps_data_chuck_validation_cnt/gps_page_size)
                print(msg, end='')

                if len(data) != CELL_GPS_IMU_READ_CHUCK_SIZE:
                    if (str_data.find(GPS_END_STR)) != -1:
                        gps_data_reading_end_flag = 0
                    elif (str_data.find(GPS_ERR_STR)) != -1:
                        if DEBUG_LOG_PRINT:
                            print(" Found GPSERR ")
                        gps_data_reading_end_flag = 1
                        gps_error_str_delete_flag = 0
                    #
                    # elif gps_data_chuck_validation_cnt > gps_page_size * 0.80:
                    #     gps_data_reading_end_flag = 0
                    else:
                        gps_data_reading_end_flag = 0
                        print("Cell reading stop other reason")

                if gps_error_str_delete_flag == 0:
                    f.write(data)
                    gps_error_str_delete_flag = 0
                gps_data_chuck_validation_cnt += 1

            print("chunk size = ", gps_data_chuck_validation_cnt)

            gps_err = bytes.fromhex(CELL_GPSERR_IMUERR_COUNT)
            ser.write(gps_err)
            error_count = ser.read(20)
            str_data = str(hex(int.from_bytes(error_count, byteorder='big')))
            cell_gps_error_count = int("0x" + str_data[12:14] + str_data[14:16], 0)
    except:
        read_error_msg = "Cell port open fail."
        # log.write_each_cell_status(serial_number, "CELL DATA READING FAIL", read_error_msg)
        read_succeed = False
        pass
    # time.sleep(1)

    # exe_time = time.time() - start_time
    # print("12312", exe_time)
    # if read_succeed:
    #     # log.write_each_cell_status(serial_number, "READING SPEND TIME", exe_time)
    print("#5")
    # read_succeed &= True

    # if callback:
    # print("callback here")
    # file_saved_callback(serial_number, read_succeed)

    new_filepath = change_filename_include_error_count(filepath, cell_gps_error_count)
    print("new path = ", new_filepath)


def read_and_save_imu_data(filepath, cell_df, callback=True):
    filename_without_ext = filename_without_extension(filepath)
    port = cell_df.loc[cell_df['file_name'] == filename_without_ext, 'port'].values[0]
    imu_page_size = cell_df.loc[cell_df['file_name'] == filename_without_ext, 'imu_page_size'].values[0]

    read_succeed = True
    imu_data_chuck_validation_cnt = 0
    # TODO : 플러그를 뽑는게 아니라 실제로 timeout 걸리는 데이터 플로우를 만들어서 체크해야함
    if DEBUG_LOG_PRINT:
        print(filepath + port + " Start reading IMU data")
        print("IM file page size = ", imu_page_size)
    with serial.Serial(port, BAUDRATE, timeout=0.1) as ser, \
            open(filepath, mode='w+b') as f:
        imu_cal = bytes.fromhex(SYSCOMMAND_SET_READ_IMU_CAL)
        ser.write(imu_cal)
        imu_cal_data = ser.read(CELL_IMU_CAL_RESP_SIZE)
        imu_cal_data = imu_cal_data[5:-3]
        f.write(imu_cal_data)

        imu = bytes.fromhex(SYSCOMMAND_OLD_UPLOAD_IMU_DATA)
        ser.write(imu)

        imu_data_reading_end_flag = 1
        imu_error_str_delete_flag = 0
        while imu_data_reading_end_flag:
            data = ser.read(CELL_GPS_IMU_READ_CHUCK_SIZE)
            str_data = str(data)

            msg = '\rIMU 진행률 %d%%\r' % (100 * imu_data_chuck_validation_cnt / imu_page_size)
            print(msg, end='')
            print()

            if len(data) != CELL_GPS_IMU_READ_CHUCK_SIZE:
                if (str_data.find(IMU_ERR_STR)) != -1:
                    if DEBUG_LOG_PRINT:
                        print(" Found IMUERR ")
                    imu_data_reading_end_flag = 1
                    imu_error_str_delete_flag = 0
                elif imu_data_chuck_validation_cnt > imu_page_size * 0.80:
                    imu_data_reading_end_flag = 0
                else:
                    imu_data_reading_end_flag = 0

                    if imu_page_size > 1728:
                        read_succeed = False
                        # cell_read_error_serial.append(filename_without_ext)

            if imu_error_str_delete_flag == 0:
                f.write(data)
                imu_error_str_delete_flag = 0
            imu_data_chuck_validation_cnt += 1

        # cell_imu_read_result.append(filename_without_ext)

        imu_err = bytes.fromhex(CELL_GPSERR_IMUERR_COUNT)
        ser.write(imu_err)
        error_count = ser.read(20)
        str_data = str(hex(int.from_bytes(error_count, byteorder='big')))
        cell_imu_error_count = int("0x" + str_data[16:18] + str_data[18:20], 0)

    # time.sleep(1)
    read_succeed &= True
    new_filepath = change_filename_include_error_count(filepath, cell_imu_error_count)
    # if callback:
    #     file_saved_callback(filepath, new_filepath, read_succeed)


def erase_cell_nand_flash(port_list, cell_df):
    hex_erase_buf = bytes.fromhex(SYSCOMMAND_ERASE_NAND_FLASH)

    for erase_nand_cell_port in port_list:
        serial_num = cell_df.loc[cell_df['port'] == erase_nand_cell_port,
                                      'serial_number'].values[0]
        try:
            ser = serial.Serial(erase_nand_cell_port, BAUDRATE, timeout=1)
            ser.write(hex_erase_buf)
            in_bin = ser.read(SYSCOMMAND_ERASE_NAND_FLASH_RESP_SIZE)
            # b'\xca`\x03\x15\x01\x01\xbc'
            print(in_bin)
            if b'\xca`\x03\x15\x01\x01\xbc' in in_bin:
                print("erase done = ", serial_num)
            else:
                print("Nand erase fail")
        except:
            print("Erase nand cell port fail = ", erase_nand_cell_port)
            pass

