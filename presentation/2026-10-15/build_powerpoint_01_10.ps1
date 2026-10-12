[CmdletBinding()]
param(
    [string]$DeckJson = '',
    [switch]$SkipPdf,
    [switch]$SkipRender
)

# New ten-slide deck only.  Existing seminar.pptx/pdf and their builder are never
# opened for writing.  Operation markers are the caller's responsibility.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$TaskRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$BuildRoot = Join-Path $TaskRoot '.build/ten-slide'
$OutputRoot = Join-Path $TaskRoot 'slides'
$RenderRoot = Join-Path $BuildRoot 'render'
if ([string]::IsNullOrWhiteSpace($DeckJson)) { $DeckJson = Join-Path $BuildRoot 'deck.json' }
$FinalPptx = Join-Path $OutputRoot 'seminar_01-10.pptx'
$FinalPdf = Join-Path $OutputRoot 'seminar_01-10.pdf'
$DraftPptx = Join-Path $BuildRoot 'draft.pptx'
$ReportPath = Join-Path $BuildRoot 'powerpoint_com_report.json'
$FontName = 'Meiryo'
$SlideWidth = 960.0
$SlideHeight = 540.0
$LayoutRecords = New-Object 'System.Collections.Generic.List[object]'
$LatticeRecords = New-Object 'System.Collections.Generic.List[object]'
$SlideRecords = New-Object 'System.Collections.Generic.List[object]'
$Warnings = New-Object 'System.Collections.Generic.List[string]'
$Report = [ordered]@{
    authoring_engine = 'Native Microsoft PowerPoint COM'
    canvas_points = @(960, 540)
    font = $FontName
    slide_count = 0
    slides = @()
    lattice_checks = @()
    layout_warnings = @()
    warnings = @()
    output = [ordered]@{}
}

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
        throw "Path is outside the presentation task directory: $absolute"
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

$Blue = Get-Color '#17365D'
$Orange = Get-Color '#E57A26'
$Ink = Get-Color '#263746'
$Muted = Get-Color '#566573'
$White = Get-Color '#FFFFFF'
$Rule = Get-Color '#D7DFE8'

function Convert-MathText {
    param([string]$Text)
    # PowerPoint stores paragraph boundaries as a single CR, so normalize before
    # computing character offsets for editable superscript/subscript runs.
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
                # Unicode superscript digits must remain superscripts, not be
                # swallowed into a preceding bare subscript such as s_i².
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

function Add-TextElement {
    param($Slide, $Element, [string]$Role = 'text')
    $x = [double](Get-Field $Element 'x' 0)
    $y = [double](Get-Field $Element 'y' 0)
    $w = [double](Get-Field $Element 'w' 100)
    $h = [double](Get-Field $Element 'h' 50)
    $size = [double](Get-Field $Element 'size' 24)
    $text = [string](Get-Field $Element 'text' '')
    $shape = $Slide.Shapes.AddTextbox(1, $x, $y, $w, $h)
    $shape.Name = "$Role-$($Slide.Shapes.Count)"
    $shape.Line.Visible = 0
    $shape.Fill.Visible = 0
    $frame = $shape.TextFrame
    $frame.MarginLeft = 0
    $frame.MarginRight = 0
    $frame.MarginTop = 0
    $frame.MarginBottom = 0
    $frame.WordWrap = $(if ([bool](Get-Field $Element 'nowrap' $false)) { 0 } else { -1 })
    $frame.AutoSize = 0
    $range = $frame.TextRange
    $math = $null
    if ([bool](Get-Field $Element 'math' $false)) { $math = Convert-MathText $text; $range.Text = $math.text } else { $range.Text = $text }
    $range.Font.Name = $FontName
    try { $range.Font.NameFarEast = $FontName } catch { }
    $range.Font.Size = $size
    $range.Font.Color.RGB = Get-Color ([string](Get-Field $Element 'color' '#263746'))
    $range.Font.Bold = $(if ([bool](Get-Field $Element 'bold' $false)) { -1 } else { 0 })
    $alignment = [string](Get-Field $Element 'align' 'left')
    $range.ParagraphFormat.Alignment = $(switch ($alignment) { 'center' { 2 } 'right' { 3 } default { 1 } })
    $range.ParagraphFormat.SpaceAfter = [double](Get-Field $Element 'space_after' 0)
    $range.ParagraphFormat.SpaceBefore = 0
    $range.ParagraphFormat.SpaceWithin = [double](Get-Field $Element 'line_spacing' 1.12)
    if ($null -ne $math) {
        foreach ($span in $math.spans) {
            $part = $range.Characters([int]$span.start, [int]$span.length)
            $part.Font.Size = $size * 0.74
            $part.Font.BaselineOffset = $(if ($span.upper) { 0.30 } else { -0.16 })
        }
    }
    $LayoutRecords.Add([ordered]@{
        slide = [int]$Slide.SlideIndex; name = $shape.Name; role = $Role
        x = $x; y = $y; w = $w; h = $h; size = $size
        text = $range.Text; source_text = $text
    })
    return $shape
}

function Add-ImageElement {
    param($Slide, $Element)
    $path = Assert-TaskPath ([string]$Element.path) -MustExist
    Add-Type -AssemblyName System.Drawing
    $image = [Drawing.Image]::FromFile($path)
    try {
        $scale = [Math]::Min([double]$Element.w / $image.Width, [double]$Element.h / $image.Height)
        $w = $image.Width * $scale
        $h = $image.Height * $scale
    } finally { $image.Dispose() }
    $x = [double]$Element.x + ([double]$Element.w - $w) / 2
    $y = [double]$Element.y + ([double]$Element.h - $h) / 2
    $shape = $Slide.Shapes.AddPicture($path, 0, -1, $x, $y, $w, $h)
    $shape.Name = 'source-or-equation-image-' + $Slide.Shapes.Count
    $shape.AlternativeText = [string](Get-Field $Element 'alt' ([IO.Path]::GetFileName($path)))
    $LayoutRecords.Add([ordered]@{ slide = [int]$Slide.SlideIndex; name = $shape.Name; role = 'image'; x = $x; y = $y; w = $w; h = $h; source = $path })
}

function Get-EdgeKey {
    param([int]$U, [int]$V)
    if ($U -lt $V) { return "$U-$V" }
    return "$V-$U"
}

function Add-LatticeElement {
    param($Slide, $Element)
    $stage = [int]$Element.stage
    if ($stage -lt 1 -or $stage -gt 4) { throw 'Lattice stage must be 1, 2, 3, or 4.' }
    $vertices = @($Element.vertices)
    if ($vertices.Count -ne 9) { throw 'The explanatory lattice must have exactly nine vertices.' }
    $points = @{}
    $coordinateKeys = @{}
    foreach ($vertex in $vertices) {
        if (@($vertex).Count -ne 3) { throw 'Each lattice vertex requires [id,x,y].' }
        $id = [int]$vertex[0]
        if ($points.ContainsKey($id)) { throw 'Duplicate vertex ID.' }
        $points[$id] = @([double]$vertex[1], [double]$vertex[2])
        $coordinateKey = '{0:R},{1:R}' -f [double]$vertex[1], [double]$vertex[2]
        if ($coordinateKeys.ContainsKey($coordinateKey)) { throw 'Duplicate lattice vertex coordinates.' }
        $coordinateKeys[$coordinateKey] = $true
    }
    $xs = @($vertices | ForEach-Object { [double]$_[1] } | Sort-Object -Unique)
    $ys = @($vertices | ForEach-Object { [double]$_[2] } | Sort-Object -Unique)
    if ($xs.Count -ne 3 -or $ys.Count -ne 3) { throw 'Vertex coordinates do not form a 3x3 lattice.' }
    $dx = [double]$xs[1] - [double]$xs[0]; $dy = [double]$ys[1] - [double]$ys[0]
    if ([Math]::Abs($dx - ([double]$xs[2] - [double]$xs[1])) -gt 0.001 -or [Math]::Abs($dy - ([double]$ys[2] - [double]$ys[1])) -gt 0.001 -or [Math]::Abs($dx - $dy) -gt 0.001) { throw 'The explanatory lattice must have equal square-lattice spacing.' }
    $expected = @{}
    foreach ($u in $points.Keys) {
        foreach ($v in $points.Keys) {
            if ([int]$u -ge [int]$v) { continue }
            $ux = [Array]::IndexOf($xs, $points[$u][0]); $uy = [Array]::IndexOf($ys, $points[$u][1])
            $vx = [Array]::IndexOf($xs, $points[$v][0]); $vy = [Array]::IndexOf($ys, $points[$v][1])
            if (([Math]::Abs($ux - $vx) + [Math]::Abs($uy - $vy)) -eq 1) { $expected[(Get-EdgeKey $u $v)] = @([int]$u, [int]$v) }
        }
    }
    if ($expected.Count -ne 12) { throw 'The initial square lattice must have twelve undirected nearest-neighbor edges.' }
    $selected = @{}
    $degrees = @{}
    foreach ($edge in @($Element.selected_edges)) {
        $u = [int]$edge[0]; $v = [int]$edge[1]; $key = Get-EdgeKey $u $v
        if (-not $expected.ContainsKey($key) -or $selected.ContainsKey($key)) { throw 'Selected path includes an invalid or repeated edge.' }
        $selected[$key] = @($u, $v)
        foreach ($id in @($u, $v)) { if (-not $degrees.ContainsKey($id)) { $degrees[$id] = 0 }; $degrees[$id]++ }
    }
    $source = [int]$Element.source; $target = [int]$Element.target
    if (-not $points.ContainsKey($source) -or -not $points.ContainsKey($target) -or $source -eq $target) { throw 'Invalid selected endpoints.' }
    $sourceX = [Array]::IndexOf($xs, $points[$source][0]); $sourceY = [Array]::IndexOf($ys, $points[$source][1])
    $targetX = [Array]::IndexOf($xs, $points[$target][0]); $targetY = [Array]::IndexOf($ys, $points[$target][1])
    $distance = [Math]::Abs($sourceX - $targetX) + [Math]::Abs($sourceY - $targetY)
    if ($selected.Count -ne 4 -or $distance -ne 4) { throw 'The selected opposite-corner shortest path must contain four edges.' }
    foreach ($id in $degrees.Keys) {
        $required = $(if ($id -eq $source -or $id -eq $target) { 1 } else { 2 })
        if ($degrees[$id] -ne $required) { throw 'The selected edges do not form a simple endpoint-to-endpoint path.' }
    }
    if (-not $degrees.ContainsKey($source) -or -not $degrees.ContainsKey($target)) { throw 'Selected path does not connect the selected vertices.' }
    $edges = @{}
    foreach ($edge in @($Element.edges)) {
        $u = [int]$edge[0]; $v = [int]$edge[1]; $key = Get-EdgeKey $u $v
        if (-not $expected.ContainsKey($key) -or $edges.ContainsKey($key)) { throw 'Displayed lattice contains an invalid or duplicate edge.' }
        $edges[$key] = @($u, $v)
    }
    $inputEdgeCount = $edges.Count
    if ($stage -eq 4 -and $edges.Count -eq 12) {
        # The JSON may carry the common initial edge set for all four panels.
        # Remove exactly the selected four path edges in the final panel.
        foreach ($key in $selected.Keys) { $edges.Remove($key) }
    }
    $requiredCount = $(if ($stage -eq 4) { 8 } else { 12 })
    if ($edges.Count -ne $requiredCount) { throw "Stage $stage must display $requiredCount edges, not $($edges.Count)." }
    foreach ($key in $expected.Keys) {
        $required = ($stage -ne 4 -or -not $selected.ContainsKey($key))
        if ($edges.ContainsKey($key) -ne $required) { throw "Stage $stage displays the wrong edge set." }
    }
    $radius = [double](Get-Field $Element 'node_diameter' 10) / 2
    foreach ($id in $points.Keys) {
        $point = $points[$id]
        if ($point[0] -lt $radius -or $point[1] -lt $radius -or $point[0] + $radius -gt [double]$Element.w -or $point[1] + $radius -gt [double]$Element.h) { throw 'Lattice vertex would extend outside its element bounds.' }
    }
    foreach ($key in ($edges.Keys | Sort-Object)) {
        $u = $edges[$key][0]; $v = $edges[$key][1]
        $edgeShape = $Slide.Shapes.AddLine(([double]$Element.x + $points[$u][0]), ([double]$Element.y + $points[$u][1]), ([double]$Element.x + $points[$v][0]), ([double]$Element.y + $points[$v][1]))
        $edgeShape.Name = "lattice-$stage-edge-$key"
        $highlight = ($stage -eq 3 -and $selected.ContainsKey($key))
        $edgeShape.Line.ForeColor.RGB = $(if ($highlight) { $Orange } else { Get-Color '#A2ADB9' })
        $edgeShape.Line.Weight = $(if ($highlight) { 3.8 } else { 2.0 })
    }
    foreach ($id in ($points.Keys | Sort-Object)) {
        $point = $points[$id]
        $node = $Slide.Shapes.AddShape(9, ([double]$Element.x + $point[0] - $radius), ([double]$Element.y + $point[1] - $radius), (2 * $radius), (2 * $radius))
        $node.Name = "lattice-$stage-vertex-$id"
        $node.Fill.ForeColor.RGB = $(if ($id -eq $source) { $Blue } elseif ($id -eq $target) { $Orange } else { Get-Color '#516274' })
        $node.Line.Visible = 0
    }
    $LatticeRecords.Add([ordered]@{
        slide = [int]$Slide.SlideIndex; stage = $stage; vertices = 9
        initial_edges = 12; selected_path_edges = 4; shortest_distance = $distance
        input_edges = $inputEdgeCount
        rendered_edges = $edges.Count; removed_edges = $(if ($stage -eq 4) { 4 } else { 0 })
        exact_edge_set_verified = $true; all_vertices_retained = $true
        selected_edge_keys = @($selected.Keys | Sort-Object)
        rendered_edge_keys = @($edges.Keys | Sort-Object)
    })
}

function Add-StandardHeader {
    param($Slide, $Definition, [int]$Index)
    if ([bool](Get-Field $Definition 'header' $true)) {
        $null = Add-TextElement $Slide ([pscustomobject]@{ x = 40; y = 34; w = 880; h = 80; text = [string]$Definition.title; size = 32; color = '#17365D'; bold = $true }) 'title'
    }
    $line = $Slide.Shapes.AddLine(40, 488, 920, 488)
    $line.Line.ForeColor.RGB = $Rule
    $line.Line.Weight = 0.7
    $null = Add-TextElement $Slide ([pscustomobject]@{ x = 40; y = 499; w = 815; h = 30; text = [string](Get-Field $Definition 'footer' ''); size = 9.5; color = '#566573' }) 'source'
    $null = Add-TextElement $Slide ([pscustomobject]@{ x = 865; y = 501; w = 55; h = 20; text = ("{0:D2} / 10" -f $Index); size = 10; color = '#566573'; align = 'right' }) 'page'
}

function Set-SpeakerNotes {
    param($Slide, [string]$Notes)
    foreach ($placeholder in $Slide.NotesPage.Shapes.Placeholders) {
        if ($placeholder.PlaceholderFormat.Type -eq 2) {
            $placeholder.TextFrame.TextRange.Text = $Notes
            $placeholder.TextFrame.TextRange.Font.Name = $FontName
            $placeholder.TextFrame.TextRange.Font.Size = 12
            return
        }
    }
    throw "Slide $($Slide.SlideIndex): notes placeholder was not found."
}

$DeckJson = Assert-TaskPath $DeckJson -MustExist
$deck = Get-Content -LiteralPath $DeckJson -Raw -Encoding utf8 | ConvertFrom-Json
$definitions = @($deck.slides)
if ($definitions.Count -ne 10) { throw "The new deck must have exactly ten slides, not $($definitions.Count)." }
for ($i = 0; $i -lt 10; $i++) {
    if ([int]$definitions[$i].id -ne $i + 1) { throw 'Slide IDs must be the ordered integers 1 through 10.' }
    if ([string]::IsNullOrWhiteSpace([string]$definitions[$i].notes)) { throw "Slide $($i + 1) requires speaker notes." }
}
$null = New-Item -ItemType Directory -Path $BuildRoot, $OutputRoot -Force
if (-not $SkipRender) { $null = New-Item -ItemType Directory -Path $RenderRoot -Force }
$application = $null; $presentation = $null; $verification = $null
$initialPresentationCount = 0; $initialAlerts = 1
try {
    $application = New-Object -ComObject PowerPoint.Application
    $initialPresentationCount = $application.Presentations.Count
    $initialAlerts = $application.DisplayAlerts
    $application.DisplayAlerts = 1
    $presentation = $application.Presentations.Add(0)
    $presentation.PageSetup.SlideWidth = $SlideWidth
    $presentation.PageSetup.SlideHeight = $SlideHeight
    for ($i = 0; $i -lt 10; $i++) {
        $definition = $definitions[$i]
        $slide = $presentation.Slides.Add($i + 1, 12)
        $slide.FollowMasterBackground = 0
        $slide.Background.Fill.ForeColor.RGB = $White
        Add-StandardHeader $slide $definition ($i + 1)
        foreach ($element in @($definition.elements)) {
            switch ([string]$element.kind) {
                'text' { $null = Add-TextElement $slide $element }
                'image' { Add-ImageElement $slide $element }
                'line' {
                    $shape = $slide.Shapes.AddLine([double]$element.x, [double]$element.y, ([double]$element.x + [double]$element.w), ([double]$element.y + [double]$element.h))
                    $shape.Name = 'layout-line-' + $slide.Shapes.Count
                    $shape.Line.ForeColor.RGB = Get-Color ([string](Get-Field $element 'color' '#D7DFE8'))
                    $shape.Line.Weight = [double](Get-Field $element 'weight' 0.8)
                }
                'lattice' { Add-LatticeElement $slide $element }
                default { throw "Unsupported element kind: $($element.kind)" }
            }
        }
        Set-SpeakerNotes $slide ([string]$definition.notes)
        $SlideRecords.Add([ordered]@{ slide = $i + 1; title = [string]$definition.title; notes_characters = ([string]$definition.notes).Length; shapes = $slide.Shapes.Count })
        Write-Output ("Created new slide {0}/10: {1}" -f ($i + 1), $definition.title)
    }
    foreach ($record in $LayoutRecords) {
        $record['outside_canvas'] = ([double]$record.x -lt 0 -or [double]$record.y -lt 0 -or ([double]$record.x + [double]$record.w) -gt ($SlideWidth + 1) -or ([double]$record.y + [double]$record.h) -gt ($SlideHeight + 1))
        if ($record.role -ne 'image') {
            $shape = $presentation.Slides.Item($record.slide).Shapes.Item($record.name)
            $record['measured_text_height'] = [double]$shape.TextFrame2.TextRange.BoundHeight
            $record['measured_text_width'] = [double]$shape.TextFrame2.TextRange.BoundWidth
            $record['vertical_overflow'] = ($record.measured_text_height -gt ([double]$record.h + 2))
            $record['horizontal_overflow'] = ($record.measured_text_width -gt ([double]$record.w + 2))
        }
    }
    # Inspect every native shape as well as the explicitly recorded text/image
    # elements, including all lattice vertices, edges, and layout rules.
    foreach ($slide in $presentation.Slides) {
        foreach ($shape in $slide.Shapes) {
            if ([double]$shape.Left -lt -1 -or [double]$shape.Top -lt -1 -or ([double]$shape.Left + [double]$shape.Width) -gt ($SlideWidth + 1) -or ([double]$shape.Top + [double]$shape.Height) -gt ($SlideHeight + 1)) {
                $LayoutRecords.Add([ordered]@{ slide = [int]$slide.SlideIndex; name = $shape.Name; role = 'native_shape'; x = [double]$shape.Left; y = [double]$shape.Top; w = [double]$shape.Width; h = [double]$shape.Height; outside_canvas = $true })
            }
        }
    }
    try { $presentation.BuiltInDocumentProperties.Item('Title').Value = '2次元正方格子上のShortest-Path Percolation — 2026年10月15日ゼミ・10枚版' } catch { }
    $presentation.SaveAs($DraftPptx, 24)
    try { $presentation.SaveAs($FinalPptx, 24, -1); $Report.output['pptx_font_embedding_requested'] = $true } catch {
        $presentation.SaveAs($FinalPptx, 24)
        $Report.output['pptx_font_embedding_requested'] = $false
        $Warnings.Add('PPTX font embedding was unavailable; editable font references are preserved. Verify PDF embedding separately.')
    }
    if (-not $SkipPdf) { $presentation.SaveCopyAs($FinalPdf, 32); $Report.output['pdf'] = $FinalPdf }
    if (-not $SkipRender) { $presentation.Export($RenderRoot, 'PNG', 1600, 900); $Report.output['render_directory'] = $RenderRoot }
    $presentation.Close(); $presentation = $null
    $verification = $application.Presentations.Open($FinalPptx, -1, 0, 0)
    if ($verification.Slides.Count -ne 10) { throw 'The saved PPTX does not contain exactly ten slides.' }
    $nativeLatticeVertices = 0; $nativeLatticeEdges = 0; $textShapes = 0; $notesPresent = 0
    foreach ($slide in $verification.Slides) {
        foreach ($shape in $slide.Shapes) {
            if ($shape.Name -like 'lattice-*-vertex-*') { $nativeLatticeVertices++ }
            if ($shape.Name -like 'lattice-*-edge-*') { $nativeLatticeEdges++ }
            if ($shape.HasTextFrame -ne 0) { $textShapes++ }
        }
        foreach ($placeholder in $slide.NotesPage.Shapes.Placeholders) {
            if ($placeholder.PlaceholderFormat.Type -eq 2 -and -not [string]::IsNullOrWhiteSpace($placeholder.TextFrame.TextRange.Text)) { $notesPresent++; break }
        }
    }
    if ($notesPresent -ne 10) { throw 'The saved PPTX is missing one or more speaker notes.' }
    $Report['slide_count'] = 10
    $Report.output['pptx'] = $FinalPptx
    $Report.output['draft_pptx'] = $DraftPptx
    $Report.output['reopened_successfully'] = $true
    $Report.output['speaker_notes_count'] = $notesPresent
    $Report.output['native_text_shapes'] = $textShapes
    $Report.output['native_lattice_vertices'] = $nativeLatticeVertices
    $Report.output['native_lattice_edges'] = $nativeLatticeEdges
    $verification.Close(); $verification = $null
} catch {
    $authoringError = $_
    $Report['fatal_error'] = [ordered]@{ message = $_.Exception.Message; line = $_.InvocationInfo.ScriptLineNumber; position = $_.InvocationInfo.PositionMessage; stack = $_.ScriptStackTrace }
    if ($null -ne $presentation -and $presentation.Slides.Count -gt 0) {
        try { $partial = Join-Path $BuildRoot 'partial_failure.pptx'; $presentation.SaveCopyAs($partial, 24); $Report.output['partial_failure_pptx'] = $partial } catch { }
    }
    throw $authoringError
} finally {
    if ($null -ne $verification) { try { $verification.Close() } catch { } }
    if ($null -ne $presentation) { try { $presentation.Close() } catch { } }
    if ($null -ne $application) {
        try { $application.DisplayAlerts = $initialAlerts } catch { }
        if ($initialPresentationCount -eq 0) { try { if ($application.Presentations.Count -eq 0) { $application.Quit() } } catch { } }
    }
    $Report['slides'] = @($SlideRecords.ToArray())
    $Report['lattice_checks'] = @($LatticeRecords.ToArray())
    $Report['layout_warnings'] = @($LayoutRecords.ToArray() | Where-Object {
        ($_.Contains('outside_canvas') -and $_['outside_canvas'] -eq $true) -or
        ($_.Contains('vertical_overflow') -and $_['vertical_overflow'] -eq $true) -or
        ($_.Contains('horizontal_overflow') -and $_['horizontal_overflow'] -eq $true)
    })
    $Report['warnings'] = @($Warnings.ToArray())
    $Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ReportPath -Encoding utf8
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
Write-Output "Saved new deck: $FinalPptx"
if (-not $SkipPdf) { Write-Output "Saved new PDF: $FinalPdf" }
Write-Output "Native verification report: $ReportPath"
