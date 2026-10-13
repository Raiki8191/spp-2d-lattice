[CmdletBinding()]
param(
    [string]$DeckJson = '',
    [switch]$SkipPdf,
    [switch]$SkipRender
)

# Append to a read-only original; never regenerate or overwrite its ten slides.
# The caller runs the presentation/PDF operation markers before this script.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$TaskRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$RepoRoot = [IO.Path]::GetFullPath((Join-Path $TaskRoot '../..'))
$BuildRoot = Join-Path $TaskRoot '.build/fss_append'
$OutputRoot = Join-Path $TaskRoot 'slides'
$RenderRoot = Join-Path $BuildRoot 'render'
if ([string]::IsNullOrWhiteSpace($DeckJson)) { $DeckJson = Join-Path $BuildRoot 'deck_fss.json' }
$OriginalPptx = Join-Path $OutputRoot 'seminar_01-10.pptx'
$FinalPptx = Join-Path $OutputRoot 'seminar_with_fss.pptx'
$FinalPdf = Join-Path $OutputRoot 'seminar_with_fss.pdf'
$DraftPptx = Join-Path $BuildRoot 'draft.pptx'
$ReportPath = Join-Path $BuildRoot 'powerpoint_com_report.json'
$ProtectionManifest = Join-Path $BuildRoot 'protected_inputs.json'
$FontName = 'Meiryo'
$SlideWidth = 960.0; $SlideHeight = 540.0
$LayoutRecords = New-Object 'System.Collections.Generic.List[object]'
$LatticeRecords = New-Object 'System.Collections.Generic.List[object]'
$SlideRecords = New-Object 'System.Collections.Generic.List[object]'
$Warnings = New-Object 'System.Collections.Generic.List[string]'
$Report = [ordered]@{
    authoring_engine = 'Native Microsoft PowerPoint COM; read-only original plus appended slides'
    canvas_points = @(960, 540)
    font = $FontName
    slide_count = 0
    slides = @()
    lattice_checks = @()
    layout_warnings = @()
    warnings = @()
    output = [ordered]@{}
}

# Reuse only the named function definitions from the existing builder.  Its
# top-level generation code is not invoked, and its file remains unchanged.
$EnginePath = Join-Path $TaskRoot 'build_powerpoint_01_10.ps1'
$parseErrors = $null; $tokens = $null
$engineAst = [Management.Automation.Language.Parser]::ParseFile($EnginePath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw 'The existing common builder has a syntax error.' }
$functionNames = @('Get-Field', 'Assert-TaskPath', 'Get-Color', 'Convert-MathText', 'Add-TextElement', 'Add-ImageElement', 'Get-EdgeKey', 'Add-LatticeElement', 'Set-SpeakerNotes')
$functions = @($engineAst.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] }, $true))
foreach ($name in $functionNames) {
    $matches = @($functions | Where-Object { $_.Name -eq $name })
    if ($matches.Count -ne 1) { throw "Expected one common function: $name" }
    . ([scriptblock]::Create($matches[0].Extent.Text))
}
$Blue = Get-Color '#17365D'; $Orange = Get-Color '#E57A26'
$Ink = Get-Color '#263746'; $Muted = Get-Color '#566573'
$White = Get-Color '#FFFFFF'; $Rule = Get-Color '#D7DFE8'

function Confirm-ProtectedInputs {
    $items = Get-Content -LiteralPath $ProtectionManifest -Raw -Encoding utf8 | ConvertFrom-Json
    $verified = @()
    foreach ($item in $items) {
        $path = [IO.Path]::GetFullPath((Join-Path $RepoRoot ([string]$item.path)))
        $prefix = $RepoRoot.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
        if (-not $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "Protected path is outside this repository: $path" }
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Protected file is missing: $path" }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne [string]$item.sha256) { throw "Protected input changed: $path" }
        $verified += [ordered]@{ path = [string]$item.path; sha256 = $actual }
    }
    return $verified
}

function Add-AppendHeader {
    param($Slide, $Definition, [int]$Index, [int]$Total)
    if ([bool](Get-Field $Definition 'header' $true)) {
        $null = Add-TextElement $Slide ([pscustomobject]@{ x = 40; y = 34; w = 880; h = 80; text = [string]$Definition.title; size = 32; color = '#17365D'; bold = $true }) 'title'
    }
    $line = $Slide.Shapes.AddLine(40, 488, 920, 488)
    $line.Line.ForeColor.RGB = $Rule; $line.Line.Weight = 0.7
    $null = Add-TextElement $Slide ([pscustomobject]@{ x = 40; y = 499; w = 815; h = 30; text = [string](Get-Field $Definition 'footer' ''); size = 9.5; color = '#566573' }) 'source'
    $null = Add-TextElement $Slide ([pscustomobject]@{ x = 865; y = 501; w = 55; h = 20; text = ("{0:D2} / {1}" -f $Index, $Total); size = 10; color = '#566573'; align = 'right' }) 'page'
}

# This checker compares original slide XML byte-for-byte after changing only
# each counter's total.  Thus all original native objects, positions, colours,
# fonts and image references must remain exactly the same.
$LegacyChecker = @'
import hashlib, json, sys, zipfile
from pathlib import Path
old_path, new_path, total = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
sha = lambda value: hashlib.sha256(value).hexdigest()
checked = []
with zipfile.ZipFile(old_path) as before, zipfile.ZipFile(new_path) as after:
    for i in range(1, 11):
        part = f"ppt/slides/slide{i}.xml"
        old = before.read(part)
        needle = f">{i:02d} / 10<".encode()
        replacement = f">{i:02d} / {total}<".encode()
        assert old.count(needle) == 1, (i, "unique original counter")
        expected = old.replace(needle, replacement)
        assert expected == after.read(part), (i, "original slide XML changed beyond its page total")
        for part in [f"ppt/slides/_rels/slide{i}.xml.rels",
                     f"ppt/notesSlides/notesSlide{i}.xml",
                     f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels"]:
            assert before.read(part) == after.read(part), (i, part, "original relationships/notes changed")
        checked.append(i)
    resources = [name for name in before.namelist() if name.startswith((
        "ppt/media/", "ppt/theme/", "ppt/slideMasters/", "ppt/slideLayouts/", "ppt/notesMasters/"))]
    for name in resources:
        assert before.read(name) == after.read(name), (name, "original resource changed")
    old_fonts = [name for name in before.namelist() if name.startswith("ppt/fonts/")]
    font_bytes_equal = all(name in after.namelist() and before.read(name) == after.read(name) for name in old_fonts)
result = {"original_slide_xml": "10/10 byte-identical except page totals",
          "original_notes_and_relationships": "10/10 byte-identical",
          "original_resources_byte_identical": len(resources),
          "original_embedded_font_resources": len(old_fonts),
          "original_embedded_font_bytes_equal": font_bytes_equal,
          "original_pptx_sha256": sha(old_path.read_bytes()),
          "old_slides_preserved": True}
print(json.dumps(result, ensure_ascii=True))
'@

$DeckJson = Assert-TaskPath $DeckJson -MustExist
$OriginalPptx = Assert-TaskPath $OriginalPptx -MustExist
$ProtectionManifest = Assert-TaskPath $ProtectionManifest -MustExist
$deck = Get-Content -LiteralPath $DeckJson -Raw -Encoding utf8 | ConvertFrom-Json
$definitions = @($deck.slides)
$TotalSlides = [int]$deck.total_slides
if ($definitions.Count -lt 1 -or $TotalSlides -ne 10 + $definitions.Count) { throw 'The total slide count does not match ten original slides plus the appendices.' }
for ($i = 0; $i -lt $definitions.Count; $i++) {
    if ([int]$definitions[$i].id -ne $i + 11) { throw 'Appended slide IDs must be consecutive starting at 11.' }
    if ([string]::IsNullOrWhiteSpace([string]$definitions[$i].notes)) { throw "Slide $($i + 11) requires speaker notes." }
}
$null = New-Item -ItemType Directory -Path $BuildRoot, $OutputRoot -Force
if (-not $SkipRender) { $null = New-Item -ItemType Directory -Path $RenderRoot -Force }
$Report['protected_inputs_before'] = @(Confirm-ProtectedInputs)
$Report['common_builder_sha256'] = (Get-FileHash -LiteralPath $EnginePath -Algorithm SHA256).Hash.ToLowerInvariant()
$application = $null; $presentation = $null; $verification = $null
$initialPresentationCount = 0; $initialAlerts = 1
try {
    $application = New-Object -ComObject PowerPoint.Application
    $initialPresentationCount = $application.Presentations.Count
    $initialAlerts = $application.DisplayAlerts; $application.DisplayAlerts = 1
    $presentation = $application.Presentations.Open($OriginalPptx, -1, 0, 0)
    if ($presentation.Slides.Count -ne 10) { throw 'The preserved original must contain exactly ten slides.' }
    if ([Math]::Abs([double]$presentation.PageSetup.SlideWidth - $SlideWidth) -gt 0.01 -or [Math]::Abs([double]$presentation.PageSetup.SlideHeight - $SlideHeight) -gt 0.01) { throw 'The preserved original canvas differs from the expected 960x540 points.' }
    $presentation.SaveAs($DraftPptx, 24)
    for ($i = 1; $i -le 10; $i++) {
        $slide = $presentation.Slides.Item($i)
        $matches = 0
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTextFrame -ne 0) {
                $range = $shape.TextFrame.TextRange
                if ($range.Text -eq ("{0:D2} / 10" -f $i)) {
                    # Replace only the final characters, preserving the run's
                    # font, alignment, colour, margins and object geometry.
                    $range.Characters(6, 2).Text = [string]$TotalSlides
                    $matches++
                    $LayoutRecords.Add([ordered]@{ slide = $i; name = $shape.Name; role = 'legacy_counter'; x = [double]$shape.Left; y = [double]$shape.Top; w = [double]$shape.Width; h = [double]$shape.Height; text = $range.Text })
                }
            }
        }
        if ($matches -ne 1) { throw "Original slide $i does not have exactly one matching page counter." }
        $SlideRecords.Add([ordered]@{ slide = $i; preserved_original = $true; shapes = $slide.Shapes.Count })
    }
    foreach ($definition in $definitions) {
        $id = [int]$definition.id
        $slide = $presentation.Slides.Add($id, 12)
        $slide.FollowMasterBackground = 0; $slide.Background.Fill.ForeColor.RGB = $White
        Add-AppendHeader $slide $definition $id $TotalSlides
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
                default { throw "Unsupported appended element kind: $($element.kind)" }
            }
        }
        Set-SpeakerNotes $slide ([string]$definition.notes)
        $SlideRecords.Add([ordered]@{ slide = $id; title = [string]$definition.title; notes_characters = ([string]$definition.notes).Length; shapes = $slide.Shapes.Count; preserved_original = $false })
        Write-Output ("Appended slide {0}/{1}: {2}" -f $id, $TotalSlides, $definition.title)
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
    foreach ($slide in $presentation.Slides) {
        foreach ($shape in $slide.Shapes) {
            if ([double]$shape.Left -lt -1 -or [double]$shape.Top -lt -1 -or ([double]$shape.Left + [double]$shape.Width) -gt ($SlideWidth + 1) -or ([double]$shape.Top + [double]$shape.Height) -gt ($SlideHeight + 1)) {
                $LayoutRecords.Add([ordered]@{ slide = [int]$slide.SlideIndex; name = $shape.Name; role = 'native_shape'; outside_canvas = $true })
            }
        }
    }
    # Inherit the original embedded fonts rather than resetting the original
    # presentation's embedding or theme settings.
    $presentation.SaveAs($FinalPptx, 24)
    $presentation.Close(); $presentation = $null
    $checkerPath = Join-Path $BuildRoot 'check_legacy_generated.py'
    $LegacyChecker | Set-Content -LiteralPath $checkerPath -Encoding utf8
    $checkOutput = & python -X utf8 -B $checkerPath $OriginalPptx $FinalPptx $TotalSlides
    if ($LASTEXITCODE -ne 0) { throw 'Strict preservation of the original ten slides failed; see the Python assertion.' }
    $Report['legacy_preservation'] = ($checkOutput -join "`n") | ConvertFrom-Json
    $verification = $application.Presentations.Open($FinalPptx, -1, 0, 0)
    if ($verification.Slides.Count -ne $TotalSlides) { throw 'The final PPTX slide count does not match the JSON.' }
    $notesPresent = 0
    foreach ($slide in $verification.Slides) {
        foreach ($placeholder in $slide.NotesPage.Shapes.Placeholders) {
            if ($placeholder.PlaceholderFormat.Type -eq 2 -and -not [string]::IsNullOrWhiteSpace($placeholder.TextFrame.TextRange.Text)) { $notesPresent++; break }
        }
    }
    if ($notesPresent -ne $TotalSlides) { throw 'One or more speaker-note pages are missing.' }
    if (-not $SkipPdf) { $verification.SaveCopyAs($FinalPdf, 32); $Report.output['pdf'] = $FinalPdf }
    if (-not $SkipRender) { $verification.Export($RenderRoot, 'PNG', 1600, 900); $Report.output['render_directory'] = $RenderRoot }
    $Report['slide_count'] = $TotalSlides
    $Report.output['pptx'] = $FinalPptx; $Report.output['draft_pptx'] = $DraftPptx
    $Report.output['reopened_successfully'] = $true
    $Report.output['speaker_notes_count'] = $notesPresent
    $verification.Close(); $verification = $null
    $Report['protected_inputs_after'] = @(Confirm-ProtectedInputs)
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
    $Report['slides'] = @($SlideRecords.ToArray()); $Report['lattice_checks'] = @($LatticeRecords.ToArray())
    $Report['layout_warnings'] = @($LayoutRecords.ToArray() | Where-Object {
        ($_.Contains('outside_canvas') -and $_['outside_canvas'] -eq $true) -or
        ($_.Contains('vertical_overflow') -and $_['vertical_overflow'] -eq $true) -or
        ($_.Contains('horizontal_overflow') -and $_['horizontal_overflow'] -eq $true)
    })
    $Report['warnings'] = @($Warnings.ToArray())
    $Report | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $ReportPath -Encoding utf8
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
Write-Output "Saved appended deck: $FinalPptx"
if (-not $SkipPdf) { Write-Output "Saved appended PDF: $FinalPdf" }
Write-Output "Preservation and layout report: $ReportPath"
