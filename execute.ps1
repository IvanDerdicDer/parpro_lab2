Set-Location "E:\python_projects\parpro_lab2";

$core_limit = [int[]](0x1,0x3,0x7,0xF,0x1F,0x3F,0x7F,0xFF);
$core_count = [int[]](1, 2, 3, 4, 5, 6, 7, 8);

$thisProcess = [System.Diagnostics.Process]::GetCurrentProcess();
"iteration|core_count|time" > time_results.csv
for ($i = 0; $i -lt 1; $i++) {
    foreach($item in $core_count) {
        $thisProcess.ProcessorAffinity = $core_limit[$item - 1];

        $timed = Measure-Command{ mpiexec.exe -n 8 python connect_four.py };

        Write-Host "$($i)|$($item)|$($timed.TotalSeconds)";
        "$($i)|$($item)|$($timed.TotalSeconds)" >> time_results.csv
    }
}