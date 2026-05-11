import os

if os.name == 'nt':
    import ctypes.wintypes


    class Kernel32:
        __HANDLE = ctypes.WinDLL('kernel32')

        IMAGE_SUBSYSTEM_WINDOWS_GUI = 2

        OFFSET_OF_E_LFANEW = 60  # noqa
        OFFSET_OF_SUBSYSTEM_FROM_PE_HEADER = (
                4 +  # size_of(PESignature)
                18 +  # offset_of(Characteristics)
                2 +  # size_of(Characteristics)
                68  # offset_of(SubSystem) both PE32 and PE32+
        )

        GetVolumeInformationW = __HANDLE.GetVolumeInformationW
        GetVolumeInformationW.argtypes = (  # noqa
            # [in, optional]  LPCWSTR lpRootPathName,
            ctypes.wintypes.LPCWSTR,
            # [out, optional] LPWSTR  lpVolumeNameBuffer,
            ctypes.wintypes.LPCWSTR,
            # [in]            DWORD   nVolumeNameSize,
            ctypes.wintypes.DWORD,
            # [out, optional] LPDWORD lpVolumeSerialNumber,  # noqa
            ctypes.wintypes.LPDWORD,
            # [out, optional] LPDWORD lpMaximumComponentLength,  # noqa
            ctypes.wintypes.LPDWORD,
            # [out, optional] LPDWORD lpFileSystemFlags,  # noqa
            ctypes.wintypes.LPDWORD,
            # [out, optional] LPWSTR  lpFileSystemNameBuffer,
            ctypes.wintypes.LPCWSTR,
            # [in]            DWORD   nFileSystemNameSize
            ctypes.wintypes.DWORD,
        )
        GetVolumeInformationW.restype = ctypes.wintypes.BOOL
