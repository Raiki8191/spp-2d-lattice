[CmdletBinding()]
param(
    [string]$DeckJson = '',
    [switch]$SkipPdf,
    [switch]$SkipRender
)

# Native Microsoft PowerPoint fallback.  No simulation is run by this script.
# All authored objects, chart data, and outputs stay in this task directory.
# Run the presentation/PDF operation markers before invoking this script.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
# PowerPoint returns an Excel _Workbook through an untyped COM interface.
# Load the installed Office type library before accessing its late-bound members.
$ExcelInterop = [Reflection.Assembly]::LoadWithPartialName('Microsoft.Office.Interop.Excel')
if ($null -eq $ExcelInterop) { throw 'The installed Microsoft Excel interop assembly is unavailable.' }

$TaskRoot = [IO.Path]::GetFullPath($PSScriptRoot)
if ([string]::IsNullOrWhiteSpace($DeckJson)) { $DeckJson = Join-Path $TaskRoot '.build/deck.json' }
$BuildRoot = Join-Path $TaskRoot '.build'
$OutputRoot = Join-Path $TaskRoot 'slides'
$RenderRoot = Join-Path $BuildRoot 'render'
$FinalPptx = Join-Path $OutputRoot 'seminar.pptx'
$FinalPdf = Join-Path $OutputRoot 'seminar.pdf'
$DraftPptx = Join-Path $BuildRoot 'draft.pptx'
$ReportPath = Join-Path $BuildRoot 'powerpoint_com_report.json'
$SlideWidth = 960.0
$SlideHeight = 540.0
$FontName = 'Meiryo'
$Report = [ordered]@{
    authoring_engine = 'Native Microsoft PowerPoint COM'
    canvas_points = @(960, 540)
    font = $FontName
    slide_count = 0
    charts = @()
    slides = @()
    layout_warnings = @()
    warnings = @()
    output = [ordered]@{}
}
$LayoutRecords = New-Object 'System.Collections.Generic.List[object]'
$ChartRecords = New-Object 'System.Collections.Generic.List[object]'
$SlideRecords = New-Object 'System.Collections.Generic.List[object]'
$WarningRecords = New-Object 'System.Collections.Generic.List[string]'

function Get-Field {
    param($Object, [string]$Name, $Default = $null)
    if ($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name]) {
        if ($null -ne $Object.$Name) { return $Object.$Name }
    }
    return $Default
}

function Assert-TaskPath {
    param([string]$Path, [switch]$MustExist)
    if (-not [IO.Path]::IsPathRooted($Path)) { $Path = Join-Path $TaskRoot $Path }
    $absolute = [IO.Path]::GetFullPath($Path)
    $prefix = $TaskRoot.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $absolute.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the task directory: $absolute"
    }
    if ($MustExist -and -not (Test-Path -LiteralPath $absolute -PathType Leaf)) {
        throw "Required input does not exist: $absolute"
    }
    return $absolute
}

function Get-Color {
    param([string]$Hex)
    $value = $Hex.TrimStart('#')
    if ($value.Length -ne 6) { throw "Invalid RGB color: $Hex" }
    $r = [Convert]::ToInt32($value.Substring(0, 2), 16)
    $g = [Convert]::ToInt32($value.Substring(2, 2), 16)
    $b = [Convert]::ToInt32($value.Substring(4, 2), 16)
    return [int]($r + ($g -shl 8) + ($b -shl 16))
}

$Ink = Get-Color '#21343B'
$Teal = Get-Color '#147D83'
$Muted = Get-Color '#52676E'
$Pale = Get-Color '#EAF3F3'
$Rule = Get-Color '#D5E1E4'
$White = Get-Color '#FFFFFF'
$Palette = @('#147D83', '#D17A27', '#425B9A', '#9C4B75', '#577A42')

function Convert-MathText {
    param([string]$Text)
    $Text = $Text.Replace("`r`n", "`r").Replace("`n", "`r")
    $plain = New-Object Text.StringBuilder
    $spans = New-Object 'System.Collections.Generic.List[object]'
    $i = 0
    while ($i -lt $Text.Length) {
        $symbol = $Text[$i]
        if (($symbol -eq '^' -or $symbol -eq '_') -and $i + 1 -lt $Text.Length) {
            $next = $i + 1
            $end = $next
            $content = ''
            if ($Text[$next] -eq '(' -or $Text[$next] -eq '{') {
                $open = $Text[$next]
                $close = $(if ($open -eq '(') { ')' } else { '}' })
                $depth = 1
                $end = $next + 1
                while ($end -lt $Text.Length -and $depth -gt 0) {
                    if ($Text[$end] -eq $open) { $depth++ }
                    if ($Text[$end] -eq $close) { $depth-- }
                    if ($depth -gt 0) { $end++ }
                }
                if ($depth -eq 0) { $content = $Text.Substring($next + 1, $end - $next - 1); $end++ }
            } else {
                $match = [regex]::Match($Text.Substring($next), '^[\p{L}0-9\p{M}∞]+')
                if ($match.Success) { $content = $match.Value; $end = $next + $content.Length }
            }
            if ($content.Length -gt 0) {
                $spans.Add([ordered]@{ start = $plain.Length + 1; length = $content.Length; upper = ($symbol -eq '^') })
                $null = $plain.Append($content)
                $i = $end
                continue
            }
        }
        $null = $plain.Append($symbol)
        $i++
    }
    return [pscustomobject]@{ text = $plain.ToString(); spans = @($spans.ToArray()) }
}

function Add-Text {
    param(
        $Slide, [string]$Text,
        [double]$X, [double]$Y, [double]$Width, [double]$Height,
        [double]$Size = 23, [int]$Color = $Ink,
        [switch]$Bold, [int]$Align = 1, [string]$Role = 'body'
    )
    $shape = $Slide.Shapes.AddTextbox(1, $X, $Y, $Width, $Height)
    $shape.Name = "$Role-$($Slide.Shapes.Count)"
    $shape.Line.Visible = 0
    $shape.Fill.Visible = 0
    $frame = $shape.TextFrame
    $frame.MarginLeft = 0
    $frame.MarginRight = 0
    $frame.MarginTop = 0
    $frame.MarginBottom = 0
    $frame.WordWrap = -1
    $frame.AutoSize = 0
    $range = $frame.TextRange
    $math = $null
    if ($Role -eq 'formula') { $math = Convert-MathText $Text; $range.Text = $math.text } else { $range.Text = $Text }
    $range.Font.Name = $FontName
    try { $range.Font.NameFarEast = $FontName } catch { }
    $range.Font.Size = $Size
    $range.Font.Color.RGB = $Color
    $range.Font.Bold = $(if ($Bold) { -1 } else { 0 })
    $range.ParagraphFormat.Alignment = $Align
    $range.ParagraphFormat.SpaceAfter = $(if ($Role -eq 'body') { 10 } else { 0 })
    $range.ParagraphFormat.SpaceBefore = 0
    $range.ParagraphFormat.SpaceWithin = 1.12
    if ($null -ne $math) {
        foreach ($span in $math.spans) {
            $part = $range.Characters([int]$span.start, [int]$span.length)
            $part.Font.Size = $Size * 0.74
            $part.Font.BaselineOffset = $(if ($span.upper) { 0.30 } else { -0.16 })
        }
    }
    $LayoutRecords.Add([ordered]@{
        slide = [int]$Slide.SlideIndex
        shape = $shape.Name
        role = $Role
        x = $X; y = $Y; width = $Width; height = $Height
        font_size = $Size
        text = $range.Text
        source_text = $Text
    })
    return $shape
}

function Add-Rule {
    param($Slide, [double]$X, [double]$Y, [double]$Width, [int]$Color = $Rule)
    $shape = $Slide.Shapes.AddLine($X, $Y, $X + $Width, $Y)
    $shape.Line.ForeColor.RGB = $Color
    $shape.Line.Weight = 0.7
}

function Add-StandardHeader {
    param($Slide, $Definition, [int]$Index, [int]$Total)
    $chapter = [string](Get-Field $Definition 'chapter' '')
    $minutes = Get-Field $Definition 'minutes' $null
    if ($null -ne $minutes -and [double]$minutes -gt 0 -and $Index -le 24) {
        $chapter += "   ／   目安 $minutes 分"
    }
    $null = Add-Text $Slide $chapter 40 20 840 20 11.5 $Teal -Bold -Role 'chapter'
    $titleSize = [double](Get-Field $Definition 'title_size' 31)
    $null = Add-Text $Slide ([string]$Definition.title) 40 53 880 74 $titleSize $Ink -Bold -Role 'title'
    Add-Rule $Slide 40 488 880
    $footer = [string](Get-Field $Definition 'footer' '')
    $null = Add-Text $Slide $footer 40 498 815 32 9.5 $Muted -Role 'source'
    $null = Add-Text $Slide ("{0:D2} / {1}" -f $Index, $Total) 864 501 56 18 10 $Muted -Align 3 -Role 'page'
}

function Add-FormulaBlock {
    param($Slide, [object[]]$Formula, [double]$X, [double]$Y, [double]$Width, [double]$Height)
    if ($Formula.Count -eq 0) { return }
    $shape = $Slide.Shapes.AddShape(1, $X, $Y, $Width, $Height)
    $shape.Fill.ForeColor.RGB = $Pale
    $shape.Line.Visible = 0
    $null = Add-Text $Slide ($Formula -join "`r`n") ($X + 16) ($Y + 12) ($Width - 32) ($Height - 24) 25 $Ink -Role 'formula'
}

function Add-BodySlide {
    param($Slide, $Definition)
    $body = @(Get-Field $Definition 'body' @())
    $formula = @(Get-Field $Definition 'formula' @())
    $size = [double](Get-Field $Definition 'body_size' $(if ($body.Count -gt 5) { 20 } elseif ($body.Count -gt 3) { 22 } else { 24 }))
    $formulaHeight = $(if ($formula.Count -gt 0) { [Math]::Min(160, 35 + 43 * $formula.Count) } else { 0 })
    $bodyHeight = 337 - $formulaHeight - $(if ($formula.Count -gt 0) { 16 } else { 0 })
    $null = Add-Text $Slide ($body -join "`r`n") 47 139 865 $bodyHeight $size $Ink -Role 'body'
    if ($formula.Count -gt 0) { Add-FormulaBlock $Slide $formula 40 (476 - $formulaHeight) 880 $formulaHeight }
}

function Add-CoverSlide {
    param($Slide, $Definition)
    # The title remains editable.  No image or decorative illustration is used.
    $null = Add-Text $Slide '卒業研究ゼミ  ／  2026年10月15日' 50 48 850 26 16 $Teal -Bold -Role 'chapter'
    $null = Add-Text $Slide ([string]$Definition.title) 50 118 850 160 36 $Ink -Bold -Role 'title'
    $null = Add-Text $Slide 'Shortest-Path Percolation（SPP）' 52 255 844 32 20 $Ink -Role 'subtitle'
    $body = @(Get-Field $Definition 'body' @())
    if ($body.Count -gt 1 -and [string]$body[0] -match '2026|10月15日|卒業研究ゼミ') { $body = @($body | Select-Object -Skip 1) }
    $null = Add-Text $Slide ($body -join "`r`n") 52 313 844 145 24 $Ink -Role 'body'
    Add-Rule $Slide 50 488 860
    $null = Add-Text $Slide ([string](Get-Field $Definition 'footer' '')) 50 499 810 30 9.5 $Muted -Role 'source'
    $null = Add-Text $Slide '01' 872 501 36 18 10 $Muted -Align 3 -Role 'page'
}

function Add-TableSlide {
    param($Slide, $Definition)
    $rows = @(Get-Field $Definition 'table' @())
    if ($rows.Count -lt 2) { throw "Slide $($Slide.SlideIndex): table requires a header and a data row." }
    $columnCount = @($rows[0]).Count
    if ($columnCount -lt 1) { throw 'Empty table header.' }
    foreach ($row in $rows) {
        if (@($row).Count -ne $columnCount) { throw "Slide $($Slide.SlideIndex): inconsistent table column counts." }
    }
    $body = @(Get-Field $Definition 'body' @())
    $formula = @(Get-Field $Definition 'formula' @())
    $afterHeight = $(if ($body.Count -ge 3) { 120 } elseif ($body.Count -gt 0 -or $formula.Count -gt 0) { 92 } else { 0 })
    $tableHeight = 333 - $afterHeight
    $tableShape = $Slide.Shapes.AddTable($rows.Count, $columnCount, 40, 139, 880, $tableHeight)
    $tableShape.Name = 'editable-comparison-table'
    $table = $tableShape.Table
    $fontSize = [double](Get-Field $Definition 'table_font' $(if ($columnCount -ge 5 -or $rows.Count -ge 8) { 16.5 } else { 19 }))
    $widths = @(Get-Field $Definition 'column_widths' @())
    if ($widths.Count -eq $columnCount) {
        $widthTotal = [double](($widths | Measure-Object -Sum).Sum)
        for ($c = 1; $c -le $columnCount; $c++) { $table.Columns.Item($c).Width = 880.0 * [double]$widths[$c - 1] / $widthTotal }
    }
    for ($r = 1; $r -le $rows.Count; $r++) {
        for ($c = 1; $c -le $columnCount; $c++) {
            $cell = $table.Cell($r, $c).Shape
            $cell.Fill.ForeColor.RGB = $(if ($r -eq 1) { $Teal } elseif ($r % 2 -eq 0) { $Pale } else { $White })
            $cell.TextFrame.MarginLeft = 10
            $cell.TextFrame.MarginRight = 10
            $cell.TextFrame.MarginTop = 7
            $cell.TextFrame.MarginBottom = 5
            # Native table cells wrap text automatically.  PowerPoint rejects
            # WordWrap/AutoSize setters on their cell-specific TextFrame.
            $cell.TextFrame.VerticalAnchor = 3
            $range = $cell.TextFrame.TextRange
            $range.Text = [string]$rows[$r - 1][$c - 1]
            $range.Font.Name = $FontName
            try { $range.Font.NameFarEast = $FontName } catch { }
            $range.Font.Size = $fontSize
            $range.Font.Bold = $(if ($r -eq 1) { -1 } else { 0 })
            $range.Font.Color.RGB = $(if ($r -eq 1) { $White } else { $Ink })
            $range.ParagraphFormat.SpaceAfter = 0
            $range.ParagraphFormat.SpaceWithin = 1.05
        }
    }
    if ($body.Count -gt 0) {
        $null = Add-Text $Slide ($body -join "`r`n") 45 (147 + $tableHeight) 870 ($afterHeight - 11) 20 $Ink -Role 'body'
    } elseif ($formula.Count -gt 0) {
        Add-FormulaBlock $Slide $formula 40 (147 + $tableHeight) 880 80
    }
}

function Add-FigureSlide {
    param($Slide, $Definition)
    $asset = Assert-TaskPath ([string]$Definition.asset) -MustExist
    Add-Type -AssemblyName System.Drawing
    $image = [Drawing.Image]::FromFile($asset)
    try {
        $scale = [Math]::Min(635.0 / $image.Width, 335.0 / $image.Height)
        $width = $image.Width * $scale
        $height = $image.Height * $scale
    } finally { $image.Dispose() }
    $picture = $Slide.Shapes.AddPicture($asset, 0, -1, (40 + (635 - $width) / 2), (138 + (335 - $height) / 2), $width, $height)
    $picture.Name = 'cited-primary-source-figure'
    $body = @(Get-Field $Definition 'body' @())
    $null = Add-Text $Slide ($body -join "`r`n") 704 143 216 327 ([double](Get-Field $Definition 'body_size' 20)) $Ink -Role 'body'
}

function Get-ExcelColumn {
    param([int]$Index)
    $result = ''
    while ($Index -gt 0) {
        $Index--
        $result = [char](65 + ($Index % 26)) + $result
        $Index = [int][Math]::Floor($Index / 26)
    }
    return $result
}

function New-NativeChart {
    param($Slide, [int]$Type, [double]$Width, [double]$Height)
    $errors = New-Object 'System.Collections.Generic.List[string]'
    # Modern default style is safer than assuming an installation has style 201.
    foreach ($method in @('modern-default', 'legacy')) {
        try {
            if ($method -eq 'modern-default') {
                return $Slide.Shapes.AddChart2(-1, $Type, 40, 139, $Width, $Height, -1)
            }
            return $Slide.Shapes.AddChart($Type, 40, 139, $Width, $Height)
        } catch {
            $errors.Add("${method}: $($_.Exception.Message)")
        }
    }
    # Some Office builds initialize the chart engine only for a presentation
    # that has a document window.  Minimize only this newly authored deck.
    $WarningRecords.Add("Slide $($Slide.SlideIndex): hidden-window chart creation failed; trying a minimized document window. $($errors -join ' | ')")
    try {
        $application.Visible = -1
        if ($initialPresentationCount -eq 0) { $application.WindowState = 2 }
        if ($presentation.Windows.Count -eq 0) {
            $window = $presentation.NewWindow()
            $window.WindowState = 2
        }
        $Slide.Select()
        Start-Sleep -Milliseconds 250
    } catch {
        $errors.Add("minimized-window initialization: $($_.Exception.Message)")
    }
    foreach ($method in @('modern-default', 'legacy')) {
        try {
            if ($method -eq 'modern-default') {
                return $Slide.Shapes.AddChart2(-1, $Type, 40, 139, $Width, $Height, -1)
            }
            return $Slide.Shapes.AddChart($Type, 40, 139, $Width, $Height)
        } catch {
            $errors.Add("minimized ${method}: $($_.Exception.Message)")
        }
    }
    throw "Native editable chart creation failed on slide $($Slide.SlideIndex). $($errors -join ' | ')"
}

function Add-ChartSlide {
    param($Slide, $Definition)
    $spec = Get-Field $Definition 'chart' $null
    if ($spec -is [string]) {
        $spec = Get-Field $deck.charts $spec $null
    }
    if ($null -eq $spec) { throw "Slide $($Slide.SlideIndex): chart definition is missing." }
    # Support compact deck-data field names as well as the explicit schema.
    foreach ($mapping in @(@('xlabel', 'x_label'), @('ylabel', 'y_label'), @('xmin', 'x_min'), @('xmax', 'x_max'), @('ymin', 'y_min'), @('ymax', 'y_max'), @('xlog', 'x_log'), @('ylog', 'y_log'))) {
        if ($null -ne $spec.PSObject.Properties[$mapping[0]] -and $null -eq $spec.PSObject.Properties[$mapping[1]]) {
            $spec | Add-Member -NotePropertyName $mapping[1] -NotePropertyValue $spec.($mapping[0])
        }
    }
    $body = @(Get-Field $Definition 'body' @())
    $formula = @(Get-Field $Definition 'formula' @())
    $wide = [bool](Get-Field $Definition 'chart_full_width' $false)
    $chartWidth = $(if ($wide) { 880 } else { 620 })
    $chartFormulaHeight = $(if ($formula.Count -gt 0) { [Math]::Min(113, 30 + 39 * $formula.Count) } else { 0 })
    $chartHeight = $(if ($wide -and $body.Count -gt 0) { 282 } elseif ($formula.Count -gt 0) { 323 - $chartFormulaHeight } else { 333 })
    $chartType = [int](Get-Field $spec 'chart_type' 75)
    $chartShape = New-NativeChart $Slide $chartType $chartWidth $chartHeight
    $chartShape.Name = 'editable-native-data-chart'
    $chart = $chartShape.Chart
    $chart.HasTitle = $false
    $chart.ChartArea.Format.Fill.ForeColor.RGB = $White
    $chart.ChartArea.Format.Line.Visible = 0
    $chart.PlotArea.Format.Fill.ForeColor.RGB = $White
    $chart.PlotArea.Format.Line.Visible = 0
    $chart.ChartArea.Font.Name = $FontName
    $chart.ChartArea.Font.Size = 14
    $seriesSpecs = @(Get-Field $spec 'series' @())
    if ($seriesSpecs.Count -eq 0) { throw 'Chart requires at least one series.' }
    $pointCounts = @()
    foreach ($s in $seriesSpecs) {
        $xs = @(Get-Field $s 'x' @())
        $ys = @(Get-Field $s 'y' @())
        if ($xs.Count -eq 0 -or $xs.Count -ne $ys.Count) { throw 'Chart X/Y array sizes do not agree.' }
        $sem = @(Get-Field $s 'sem' @())
        if ($sem.Count -gt 0 -and $sem.Count -ne $ys.Count) { throw 'SEM array size does not agree with Y.' }
        for ($p = 0; $p -lt $ys.Count; $p++) {
            if ([double]::IsNaN([double]$ys[$p]) -or [double]::IsInfinity([double]$ys[$p])) { throw 'Chart contains a non-finite Y value.' }
            if ([bool](Get-Field $spec 'x_log' $false) -and [double]$xs[$p] -le 0) { throw 'Logarithmic X values must be positive.' }
            if ($sem.Count -gt 0 -and [double]$sem[$p] -lt 0) { throw 'SEM must be non-negative.' }
        }
        $pointCounts += $xs.Count
    }
    $maxPoints = [int](($pointCounts | Measure-Object -Maximum).Maximum)
    $columnCount = $seriesSpecs.Count * 3
    $data = [Array]::CreateInstance([object], [int[]]@(($maxPoints + 1), $columnCount))
    for ($i = 0; $i -lt $seriesSpecs.Count; $i++) {
        $s = $seriesSpecs[$i]
        $name = [string](Get-Field $s 'name' "系列 $($i + 1)")
        $xs = @($s.x); $ys = @($s.y); $sem = @(Get-Field $s 'sem' @())
        $data[0, ($i * 3)] = "$name : X"
        $data[0, ($i * 3 + 1)] = $name
        $data[0, ($i * 3 + 2)] = "$name : 標準誤差"
        for ($p = 0; $p -lt $ys.Count; $p++) {
            $data[($p + 1), ($i * 3)] = [double]$xs[$p]
            $data[($p + 1), ($i * 3 + 1)] = [double]$ys[$p]
            if ($sem.Count -gt 0) { $data[($p + 1), ($i * 3 + 2)] = [double]$sem[$p] }
        }
    }
    $workbook = $null
    $excelApp = $null
    $wasExcelVisible = $false
    try {
        # The workbook is embedded in the PPTX, so the recipient can edit the data.
        if ($presentation.Windows.Count -eq 0) {
            $application.Visible = -1
            $window = $presentation.NewWindow()
            $window.WindowState = 2
        }
        $chart.ChartData.ActivateChartDataWindow()
        Start-Sleep -Milliseconds 200
        for ($attempt = 0; $attempt -lt 8; $attempt++) {
            $workbook = $chart.ChartData.Workbook
            if ($null -ne $workbook) { break }
            Start-Sleep -Milliseconds 200
        }
        if ($null -eq $workbook) {
            $chart.ChartData.ActivateChartDataWindow()
            Start-Sleep -Milliseconds 500
            $workbook = $chart.ChartData.Workbook
        }
        if ($null -eq $workbook) { throw 'PowerPoint did not initialize its embedded Excel workbook.' }
        # A freshly created chart may expose only IDispatch until its type
        # information is queried.  Reflection avoids that first-access cache.
        $excelApp = $workbook.GetType().InvokeMember('Application', [Reflection.BindingFlags]::GetProperty, $null, $workbook, $null)
        $wasExcelVisible = [bool]$excelApp.Visible
        $excelApp.Visible = $false
        $sheets = $workbook.GetType().InvokeMember('Worksheets', [Reflection.BindingFlags]::GetProperty, $null, $workbook, $null)
        $sheet = $sheets.Item(1)
        $sheet.Name = 'データ'
        $sheet.Cells.Clear()
        $lastColumn = Get-ExcelColumn $columnCount
        $sheet.Range("A1:${lastColumn}$($maxPoints + 1)").Value2 = $data
        while ($chart.SeriesCollection().Count -gt 0) { $chart.SeriesCollection(1).Delete() }
        for ($i = 0; $i -lt $seriesSpecs.Count; $i++) {
            $s = $seriesSpecs[$i]
            $count = $pointCounts[$i]
            $xColumn = Get-ExcelColumn ($i * 3 + 1)
            $yColumn = Get-ExcelColumn ($i * 3 + 2)
            $semColumn = Get-ExcelColumn ($i * 3 + 3)
            $series = $chart.SeriesCollection().NewSeries()
            $series.Name = [string](Get-Field $s 'name' "系列 $($i + 1)")
            # Use embedded-sheet formulas rather than passing Excel Range
            # interfaces across the PowerPoint/Excel COM boundary.
            $xFormula = "='データ'!" + '$' + $xColumn + '$2:$' + $xColumn + '$' + ($count + 1)
            $yFormula = "='データ'!" + '$' + $yColumn + '$2:$' + $yColumn + '$' + ($count + 1)
            $series.XValues = $xFormula
            $series.Values = $yFormula
            $series.Format.Line.ForeColor.RGB = Get-Color ([string](Get-Field $s 'color' $Palette[$i % $Palette.Count]))
            $series.Format.Line.Weight = [double](Get-Field $s 'line_width' 2)
            $series.Smooth = $false
            $hasMarkers = [bool](Get-Field $s 'markers' $(Get-Field $spec 'markers' $false))
            $series.MarkerStyle = $(if ($hasMarkers) { 8 } else { -4142 })
            if ($hasMarkers) {
                $series.MarkerSize = 6
                $series.MarkerForegroundColor = $series.Format.Line.ForeColor.RGB
                $series.MarkerBackgroundColor = $White
            }
            if ([bool](Get-Field $s 'line_hidden' $false)) { $series.Format.Line.Visible = 0 }
            $sem = @(Get-Field $s 'sem' @())
            if ($sem.Count -gt 0) {
                $errFormula = "='データ'!" + '$' + $semColumn + '$2:$' + $semColumn + '$' + ($count + 1)
                $series.ErrorBar(1, 1, -4114, $errFormula, $errFormula)
                $series.ErrorBars.EndStyle = 1
                $series.ErrorBars.Format.Line.ForeColor.RGB = $series.Format.Line.ForeColor.RGB
                $series.ErrorBars.Format.Line.Weight = 1
            }
        }
        # Observed-curve endpoints are marked separately without extending data.
        # These native marker series are not independent observations.
        $endpointSeriesIndices = @()
        for ($i = 0; $i -lt $seriesSpecs.Count; $i++) {
            $s = $seriesSpecs[$i]
            $endpoint = @(Get-Field $s 'end' @())
            if ($endpoint.Count -eq 2) {
                $endpointSeries = $chart.SeriesCollection().NewSeries()
                $endpointSeries.Name = '共通観測範囲の終端'
                $endpointSeries.XValues = [double[]]@([double]$endpoint[0])
                $endpointSeries.Values = [double[]]@([double]$endpoint[1])
                $endpointSeries.Format.Line.Visible = 0
                $endpointSeries.MarkerStyle = 8
                $endpointSeries.MarkerSize = 7
                $endpointSeries.MarkerForegroundColor = Get-Color ([string](Get-Field $s 'color' $Palette[$i % $Palette.Count]))
                $endpointSeries.MarkerBackgroundColor = $White
                $endpointSeriesIndices += $chart.SeriesCollection().Count
            }
        }
        $workbook.Close($true)
        $workbook = $null
        # Never quit an Excel application that may contain the user's workbooks.
        if ($wasExcelVisible -and $excelApp.Workbooks.Count -gt 0) { $excelApp.Visible = $true }
    } finally {
        if ($null -ne $workbook) { try { $workbook.Close($false) } catch { } }
    }
    $xAxis = $chart.Axes(1, 1)
    $yAxis = $chart.Axes(2, 1)
    foreach ($axis in @($xAxis, $yAxis)) {
        $axis.HasTitle = $true
        $axis.TickLabels.Font.Name = $FontName
        $axis.TickLabels.Font.Size = 14
        $axis.Format.Line.ForeColor.RGB = $Muted
        $axis.Format.Line.Weight = 0.8
        $axis.AxisTitle.Font.Name = $FontName
        $axis.AxisTitle.Font.Size = 15
        $axis.AxisTitle.Font.Color = $Ink
    }
    $xAxis.AxisTitle.Text = [string](Get-Field $spec 'x_label' '')
    $yAxis.AxisTitle.Text = [string](Get-Field $spec 'y_label' '')
    $xAxis.ScaleType = $(if ([bool](Get-Field $spec 'x_log' $false)) { -4133 } else { -4132 })
    $yAxis.ScaleType = $(if ([bool](Get-Field $spec 'y_log' $false)) { -4133 } else { -4132 })
    foreach ($pair in @(@($xAxis, 'x'), @($yAxis, 'y'))) {
        $axis = $pair[0]; $prefix = [string]$pair[1]
        $minimum = Get-Field $spec ($prefix + '_min') $null
        $maximum = Get-Field $spec ($prefix + '_max') $null
        $major = Get-Field $spec ($prefix + '_major') $null
        if ($null -ne $minimum) { $axis.MinimumScale = [double]$minimum }
        if ($null -ne $maximum) { $axis.MaximumScale = [double]$maximum }
        if ($null -ne $major) { $axis.MajorUnit = [double]$major }
        $format = Get-Field $spec ($prefix + '_format') $null
        if ($null -ne $format) { $axis.TickLabels.NumberFormat = [string]$format }
    }
    $xAxis.HasMajorGridlines = $false
    $yAxis.HasMajorGridlines = [bool](Get-Field $spec 'y_grid' $false)
    if ($yAxis.HasMajorGridlines) {
        $yAxis.MajorGridlines.Format.Line.ForeColor.RGB = $Rule
        $yAxis.MajorGridlines.Format.Line.Weight = 0.5
    }
    $chart.HasLegend = [bool](Get-Field $spec 'legend' ($seriesSpecs.Count -gt 1))
    if ($chart.HasLegend) {
        $chart.Legend.Position = -4160
        $chart.Legend.Font.Name = $FontName
        $chart.Legend.Font.Size = 13
        $chart.Legend.Format.Fill.Visible = 0
        $chart.Legend.Format.Line.Visible = 0
        for ($i = $endpointSeriesIndices.Count - 1; $i -ge 0; $i--) {
            $chart.Legend.LegendEntries($endpointSeriesIndices[$i]).Delete()
        }
    }
    if ($body.Count -gt 0) {
        if ($wide) {
            $null = Add-Text $Slide ($body -join "`r`n") 45 427 875 49 19 $Ink -Role 'body'
        } else {
            $bodyHeight = $(if ($formula.Count -gt 0) { $chartHeight - 7 } else { 326 })
            $null = Add-Text $Slide ($body -join "`r`n") 680 146 240 $bodyHeight ([double](Get-Field $Definition 'body_size' 20)) $Ink -Role 'body'
        }
    }
    if ($formula.Count -gt 0) {
        Add-FormulaBlock $Slide $formula 40 (476 - $chartFormulaHeight) 880 $chartFormulaHeight
    }
    $ChartRecords.Add([ordered]@{
        slide = [int]$Slide.SlideIndex
        title = [string]$Definition.title
        series_names = @($seriesSpecs | ForEach-Object { $_.name })
        point_counts = $pointCounts
        sem_errorbars = @($seriesSpecs | ForEach-Object { @(Get-Field $_ 'sem' @()).Count -gt 0 })
        embedded_workbook = $true
        x_log = [bool](Get-Field $spec 'x_log' $false)
        y_log = [bool](Get-Field $spec 'y_log' $false)
        smoothing = $false
    })
}

function Set-SpeakerNotes {
    param($Slide, [string]$Notes)
    $found = $false
    foreach ($placeholder in $Slide.NotesPage.Shapes.Placeholders) {
        if ($placeholder.PlaceholderFormat.Type -eq 2) {
            $placeholder.TextFrame.TextRange.Text = $Notes
            $placeholder.TextFrame.TextRange.Font.Name = $FontName
            $placeholder.TextFrame.TextRange.Font.Size = 12
            $found = $true
            break
        }
    }
    if (-not $found) { throw "Slide $($Slide.SlideIndex): speaker-notes placeholder was not found." }
}

$DeckJson = Assert-TaskPath $DeckJson -MustExist
$deck = Get-Content -LiteralPath $DeckJson -Raw -Encoding utf8 | ConvertFrom-Json
$definitions = @($deck.slides)
if ($definitions.Count -eq 0) { throw 'No slides are specified.' }
$null = New-Item -ItemType Directory -Path $BuildRoot, $OutputRoot -Force
if (-not $SkipRender) { $null = New-Item -ItemType Directory -Path $RenderRoot -Force }
$application = $null
$presentation = $null
$verification = $null
$initialPresentationCount = 0
try {
    $application = New-Object -ComObject PowerPoint.Application
    $initialPresentationCount = $application.Presentations.Count
    $application.DisplayAlerts = 1
    $presentation = $application.Presentations.Add(0)
    $presentation.PageSetup.SlideWidth = $SlideWidth
    $presentation.PageSetup.SlideHeight = $SlideHeight
    for ($i = 0; $i -lt $definitions.Count; $i++) {
        $definition = $definitions[$i]
        $slide = $presentation.Slides.Add($i + 1, 12)
        $slide.FollowMasterBackground = 0
        $slide.Background.Fill.ForeColor.RGB = $White
        $type = [string](Get-Field $definition 'type' 'body')
        if ($type -eq 'cover') {
            Add-CoverSlide $slide $definition
        } else {
            Add-StandardHeader $slide $definition ($i + 1) $definitions.Count
            switch ($type) {
                'table' { Add-TableSlide $slide $definition }
                'figure' { Add-FigureSlide $slide $definition }
                'chart' { Add-ChartSlide $slide $definition }
                'native_curve' { Add-ChartSlide $slide $definition }
                'native_jump' { Add-ChartSlide $slide $definition }
                'concept_chart' { Add-ChartSlide $slide $definition }
                'concept' { Add-ChartSlide $slide $definition }
                'curve' { Add-ChartSlide $slide $definition }
                'jump' { Add-ChartSlide $slide $definition }
                default { Add-BodySlide $slide $definition }
            }
        }
        $notes = [string](Get-Field $definition 'notes' '')
        if ([string]::IsNullOrWhiteSpace($notes)) { throw "Slide $($i + 1): speaker notes are required." }
        Set-SpeakerNotes $slide $notes
        $SlideRecords.Add([ordered]@{
            slide = $i + 1
            id = Get-Field $definition 'id' ($i + 1)
            title = [string]$definition.title
            type = $type
            notes_characters = $notes.Length
        })
        Write-Output ("Created slide {0}/{1}: {2}" -f ($i + 1), $definitions.Count, $definition.title)
    }
    try { $presentation.BuiltInDocumentProperties.Item('Title').Value = '2026年10月15日 卒業研究ゼミ：2次元正方格子上のSPP' } catch { }
    try { $presentation.BuiltInDocumentProperties.Item('Subject').Value = '一次資料に基づくパーコレーション・SPP・有限サイズ解析の説明' } catch { }
    try { $presentation.BuiltInDocumentProperties.Item('Author').Value = '卒業研究ゼミ資料' } catch { }
    # Geometry and text-fit measurements are recorded before the native export.
    foreach ($record in $LayoutRecords) {
        $shape = $presentation.Slides.Item($record.slide).Shapes.Item($record.shape)
        try {
            $boundHeight = [double]$shape.TextFrame2.TextRange.BoundHeight
            $record['measured_text_height'] = $boundHeight
            $record['vertical_overflow'] = ($boundHeight -gt ([double]$record.height + 2))
        } catch {
            $record['measured_text_height'] = $null
            $record['vertical_overflow'] = $null
        }
        $record['outside_canvas'] = ([double]$record.x -lt 0 -or [double]$record.y -lt 0 -or ([double]$record.x + [double]$record.width) -gt ($SlideWidth + 1) -or ([double]$record.y + [double]$record.height) -gt ($SlideHeight + 1))
    }
    $presentation.SaveAs($DraftPptx, 24)
    try {
        $presentation.SaveAs($FinalPptx, 24, -1)
        $Report.output['pptx_font_embedding_requested'] = $true
    } catch {
        $WarningRecords.Add('PowerPoint could not save with EmbedTrueTypeFonts enabled; the PPTX was saved with its editable font references. Check PDF font embedding separately.')
        $presentation.SaveAs($FinalPptx, 24)
        $Report.output['pptx_font_embedding_requested'] = $false
    }
    if (-not $SkipPdf) {
        try { $presentation.ExportAsFixedFormat($FinalPdf, 2, 2) } catch {
            # PowerShell 5.1 can misbind the optional COM arguments on this
            # Office method.  SaveCopyAs uses the same native PDF exporter.
            $presentation.SaveCopyAs($FinalPdf, 32)
            $WarningRecords.Add('ExportAsFixedFormat COM argument binding was unavailable; native SaveCopyAs(PDF) was used.')
        }
        $Report.output['pdf'] = $FinalPdf
    }
    if (-not $SkipRender) {
        $presentation.Export($RenderRoot, 'PNG', 1600, 900)
        $Report.output['render_directory'] = $RenderRoot
    }
    $presentation.Close()
    $presentation = $null
    $verification = $application.Presentations.Open($FinalPptx, -1, 0, 0)
    if ($verification.Slides.Count -ne $definitions.Count) { throw 'Saved PPTX slide count does not agree with the specification.' }
    $nativeChartCount = 0
    $nativeTableCount = 0
    foreach ($slide in $verification.Slides) {
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasChart -ne 0) { $nativeChartCount++ }
            if ($shape.HasTable -ne 0) { $nativeTableCount++ }
        }
    }
    $Report['slide_count'] = $verification.Slides.Count
    $Report.output['pptx'] = $FinalPptx
    $Report.output['draft_pptx'] = $DraftPptx
    $Report.output['reopened_successfully'] = $true
    $Report.output['native_chart_count'] = $nativeChartCount
    $Report.output['native_table_count'] = $nativeTableCount
    $verification.Close()
    $verification = $null
} catch {
    $authoringError = $_
    $Report['fatal_error'] = [ordered]@{
        message = $_.Exception.Message
        line = $_.InvocationInfo.ScriptLineNumber
        position = $_.InvocationInfo.PositionMessage
        script_stack = $_.ScriptStackTrace
    }
    if ($null -ne $presentation -and $presentation.Slides.Count -gt 0) {
        try {
            $partial = Join-Path $BuildRoot 'partial_failure.pptx'
            $presentation.SaveCopyAs($partial, 24)
            $Report.output['partial_failure_pptx'] = $partial
        } catch {
            $WarningRecords.Add("Could not save partial failure deck: $($_.Exception.Message)")
        }
    }
    throw $authoringError
} finally {
    if ($null -ne $verification) { try { $verification.Close() } catch { } }
    if ($null -ne $presentation) { try { $presentation.Close() } catch { } }
    if ($null -ne $application -and $initialPresentationCount -eq 0) {
        try { if ($application.Presentations.Count -eq 0) { $application.Quit() } } catch { }
    }
    $Report['charts'] = @($ChartRecords.ToArray())
    $Report['slides'] = @($SlideRecords.ToArray())
    $Report['layout_warnings'] = @($LayoutRecords.ToArray() | Where-Object {
        ($_.Contains('vertical_overflow') -and $_['vertical_overflow'] -eq $true) -or
        ($_.Contains('outside_canvas') -and $_['outside_canvas'] -eq $true)
    })
    $Report['warnings'] = @($WarningRecords.ToArray())
    $Report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ReportPath -Encoding utf8
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
Write-Output "Saved: $FinalPptx"
if (-not $SkipPdf) { Write-Output "Saved: $FinalPdf" }
Write-Output "Native validation report: $ReportPath"
