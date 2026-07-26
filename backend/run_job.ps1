$logPath = "C:\Users\谢键荣\SmartMall-AI\backend\job_error.log"
try {
    $output = & "D:\Anaconda\python.exe" "C:\Users\谢键荣\SmartMall-AI\backend\server.py" 2>&1
    $output | Out-File -FilePath $logPath -Encoding utf8
} catch {
    "EXCEPTION: $_" | Out-File -FilePath $logPath -Encoding utf8
    $_.Exception | Format-List -Force | Out-File -FilePath $logPath -Append -Encoding utf8
}
