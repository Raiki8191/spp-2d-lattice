[CmdletBinding()]
param([switch]$SkipPdf, [switch]$SkipRender)

# Only this task's new filenames are written. Original parts are transplanted
# unchanged after editing just slides 11-14 in a private native COM draft.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$TaskRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$RepoRoot = [IO.Path]::GetFullPath((Join-Path $TaskRoot '../..'))
$BuildRoot = Join-Path $TaskRoot '.build/ver1_slides'
$OutputRoot = Join-Path $TaskRoot 'slides'
$OriginalPptx = Join-Path $OutputRoot 'seminar_with_fss.pptx'
$OriginalPdf = Join-Path $OutputRoot 'seminar_with_fss.pdf'
$FinalPptx = Join-Path $OutputRoot 'seminar_ver1.pptx'
$FinalPdf = Join-Path $OutputRoot 'seminar_ver1.pdf'
$DraftPptx = Join-Path $BuildRoot 'native_draft.pptx'
$CandidatePptx = Join-Path $BuildRoot 'native_candidate.pptx'
$NativePdf = Join-Path $BuildRoot 'native_full.pdf'
$ReportPath = Join-Path $BuildRoot 'powerpoint_com_report.json'
$FontName = 'Meiryo'
$SlideWidth = 960.0; $SlideHeight = 540.0
$LayoutRecords = New-Object 'System.Collections.Generic.List[object]'
$LatticeRecords = New-Object 'System.Collections.Generic.List[object]'
$Warnings = New-Object 'System.Collections.Generic.List[string]'
$Report = [ordered]@{
    authoring_engine = 'Microsoft PowerPoint COM; only slides 11-14; exact original ZIP transplant'
    canvas_points = @(960, 540); font = $FontName; slide_count = 0
    revised_slide_numbers = @(11, 12, 13, 14); layout_warnings = @(); output = [ordered]@{}
}

$EnginePath = Join-Path $TaskRoot 'build_powerpoint_01_10.ps1'
$parseErrors = $null; $tokens = $null
$engineAst = [Management.Automation.Language.Parser]::ParseFile($EnginePath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw 'The existing builder has a syntax error.' }
$functionNames = @('Get-Field', 'Assert-TaskPath', 'Get-Color', 'Convert-MathText', 'Add-TextElement', 'Add-ImageElement', 'Set-SpeakerNotes')
$functions = @($engineAst.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] }, $true))
foreach ($name in $functionNames) {
    $matches = @($functions | Where-Object { $_.Name -eq $name })
    if ($matches.Count -ne 1) { throw "Expected one common function: $name" }
    . ([scriptblock]::Create($matches[0].Extent.Text))
}
$White = Get-Color '#FFFFFF'; $Rule = Get-Color '#D7DFE8'

function Confirm-ProtectedInputs {
    $items = Get-Content -LiteralPath (Join-Path $BuildRoot 'protected_inputs.json') -Raw -Encoding utf8 | ConvertFrom-Json
    $verified = @()
    foreach ($item in $items) {
        $path = [IO.Path]::GetFullPath((Join-Path $RepoRoot ([string]$item.path)))
        if (-not $path.StartsWith($RepoRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Protected path is outside repository.' }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne [string]$item.sha256) { throw "Protected input changed: $path" }
        $verified += [ordered]@{ path = [string]$item.path; sha256 = $actual }
    }
    return $verified
}

function Add-Ver1Header {
    param($Slide, $Definition, [int]$Index)
    $null = Add-TextElement $Slide ([pscustomobject]@{ x = 40; y = 34; w = 880; h = 80; text = [string]$Definition.title; size = 32; color = '#17365D'; bold = $true }) 'title'
    $line = $Slide.Shapes.AddLine(40, 488, 920, 488)
    $line.Line.ForeColor.RGB = $Rule; $line.Line.Weight = 0.7
    $null = Add-TextElement $Slide ([pscustomobject]@{ x = 40; y = 499; w = 815; h = 30; text = [string]$Definition.footer; size = 9.5; color = '#566573' }) 'source'
    $null = Add-TextElement $Slide ([pscustomobject]@{ x = 865; y = 501; w = 55; h = 20; text = ("{0:D2} / 23" -f $Index); size = 10; color = '#566573'; align = 'right' }) 'page'
}

$deck = Get-Content -LiteralPath (Join-Path $BuildRoot 'deck_ver1.json') -Raw -Encoding utf8 | ConvertFrom-Json
if ($deck.total_slides -ne 23 -or $deck.slides.Count -ne 4) { throw 'Only four replacement slides are allowed in a 23-slide deck.' }
$null = New-Item -ItemType Directory -Path $BuildRoot, $OutputRoot -Force
$Report['protected_inputs_before'] = @(Confirm-ProtectedInputs)
$application = $null; $presentation = $null; $verification = $null
$initialAlerts = 1
try {
    $application = New-Object -ComObject PowerPoint.Application
    $initialAlerts = $application.DisplayAlerts; $application.DisplayAlerts = 1
    Copy-Item -LiteralPath $OriginalPptx -Destination $DraftPptx -Force
    $presentation = $application.Presentations.Open($DraftPptx, 0, 0, 0)
    if ($presentation.Slides.Count -ne 23) { throw 'Original must contain 23 slides.' }
    if ([Math]::Abs([double]$presentation.PageSetup.SlideWidth - $SlideWidth) -gt .01 -or [Math]::Abs([double]$presentation.PageSetup.SlideHeight - $SlideHeight) -gt .01) { throw 'Unexpected canvas.' }
    foreach ($definition in $deck.slides) {
        $id = [int]$definition.id
        if ($id -lt 11 -or $id -gt 14) { throw 'Replacement slide outside approved scope.' }
        $slide = $presentation.Slides.Item($id)
        for ($j = $slide.Shapes.Count; $j -gt 0; $j--) { $slide.Shapes.Item($j).Delete() }
        $slide.FollowMasterBackground = 0; $slide.Background.Fill.ForeColor.RGB = $White
        Add-Ver1Header $slide $definition $id
        foreach ($element in $definition.elements) {
            switch ([string]$element.kind) {
                'text' { $null = Add-TextElement $slide $element }
                'image' { Add-ImageElement $slide $element }
                default { throw 'Only text and existing-method math images are expected.' }
            }
        }
        Set-SpeakerNotes $slide ([string]$definition.notes)
        Write-Output ("Revised slide {0}/23: {1}" -f $id, $definition.title)
    }
    foreach ($record in $LayoutRecords) {
        $record['outside_canvas'] = ([double]$record.x -lt 0 -or [double]$record.y -lt 0 -or ([double]$record.x + [double]$record.w) -gt 961 -or ([double]$record.y + [double]$record.h) -gt 541)
        if ($record.role -ne 'image') {
            $shape = $presentation.Slides.Item($record.slide).Shapes.Item($record.name)
            $record['measured_text_height'] = [double]$shape.TextFrame2.TextRange.BoundHeight
            $record['measured_text_width'] = [double]$shape.TextFrame2.TextRange.BoundWidth
            $record['vertical_overflow'] = ($record.measured_text_height -gt ([double]$record.h + 2))
            $record['horizontal_overflow'] = ($record.measured_text_width -gt ([double]$record.w + 2))
        }
    }
    $presentation.Saved = 0
    $presentation.SaveCopyAs($CandidatePptx, 24)
    $presentation.Close(); $presentation = $null
    & python -X utf8 -B (Join-Path $TaskRoot 'prepare_ver1.py') --merge $CandidatePptx
    if ($LASTEXITCODE -ne 0) { throw 'Exact original-package preservation failed.' }
    $verification = $application.Presentations.Open($FinalPptx, -1, 0, 0)
    if ($verification.Slides.Count -ne 23) { throw 'Final does not have 23 slides.' }
    $notes = 0
    foreach ($slide in $verification.Slides) {
        $counter = 0
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTextFrame -ne 0 -and $shape.TextFrame.TextRange.Text -eq ("{0:D2} / 23" -f $slide.SlideIndex)) { $counter++ }
        }
        if ($counter -ne 1) { throw "Missing or inconsistent page counter: $($slide.SlideIndex)" }
        foreach ($placeholder in $slide.NotesPage.Shapes.Placeholders) {
            if ($placeholder.PlaceholderFormat.Type -eq 2 -and -not [string]::IsNullOrWhiteSpace($placeholder.TextFrame.TextRange.Text)) { $notes++; break }
        }
    }
    if ($notes -ne 23) { throw 'Missing speaker notes.' }
    if (-not $SkipPdf) { $verification.SaveCopyAs($NativePdf, 32) }
    if (-not $SkipRender) {
        $render = Join-Path $BuildRoot 'native_render'
        $null = New-Item -ItemType Directory -Path $render -Force
        foreach ($id in @(11, 12, 13, 14)) { $verification.Slides.Item($id).Export((Join-Path $render ("slide-{0:D2}.png" -f $id)), 'PNG', 1600, 900) }
        $Report.output['native_render_directory'] = $render
    }
    $verification.Close(); $verification = $null
    if (-not $SkipPdf) {
        $pages = Join-Path $BuildRoot 'pdf_pages'
        $null = New-Item -ItemType Directory -Path $pages -Force
        & pdfseparate $OriginalPdf (Join-Path $pages 'original-%d.pdf')
        if ($LASTEXITCODE -ne 0) { throw 'Original PDF page extraction failed.' }
        & pdfseparate -f 11 -l 14 $NativePdf (Join-Path $pages 'replacement-%d.pdf')
        if ($LASTEXITCODE -ne 0) { throw 'Replacement PDF page extraction failed.' }
        $parts = @()
        for ($i = 1; $i -le 23; $i++) {
            $prefix = $(if ($i -ge 11 -and $i -le 14) { 'replacement-' } else { 'original-' })
            $parts += (Join-Path $pages ($prefix + $i + '.pdf'))
        }
        & pdfunite @parts $FinalPdf
        if ($LASTEXITCODE -ne 0) { throw 'Exact preserved-page PDF concatenation failed.' }
        $Report.output['pdf'] = $FinalPdf
        $Report['pdf_preservation_method'] = 'Original page objects for 1-10 and 15-23; native exported replacement pages 11-14; pdfunite only.'
        if (-not $SkipRender) {
            $pdfRender = Join-Path $BuildRoot 'pdf'
            $null = New-Item -ItemType Directory -Path $pdfRender -Force
            & pdftoppm -f 11 -l 14 -r 120 -png $FinalPdf (Join-Path $pdfRender 'ver1')
            if ($LASTEXITCODE -ne 0) { throw 'Final PDF render failed.' }
            $Report.output['pdf_render_directory'] = $pdfRender
        }
    }
    $Report['slide_count'] = 23
    $Report.output['pptx'] = $FinalPptx
    $Report.output['reopened_successfully'] = $true
    $Report.output['speaker_notes_count'] = $notes
    $Report['protected_inputs_after'] = @(Confirm-ProtectedInputs)
} catch {
    $Report['fatal_error'] = [ordered]@{ message = $_.Exception.Message; line = $_.InvocationInfo.ScriptLineNumber; stack = $_.ScriptStackTrace }
    throw
} finally {
    if ($null -ne $verification) { try { $verification.Close() } catch {} }
    if ($null -ne $presentation) { try { $presentation.Close() } catch {} }
    if ($null -ne $application) { try { $application.DisplayAlerts = $initialAlerts } catch {} }
    # Do not quit PowerPoint or close any user-owned presentation.
    $Report['layout_records'] = @($LayoutRecords.ToArray())
    $Report['layout_warnings'] = @($LayoutRecords.ToArray() | Where-Object {
        ($_.Contains('outside_canvas') -and $_['outside_canvas'] -eq $true) -or
        ($_.Contains('vertical_overflow') -and $_['vertical_overflow'] -eq $true) -or
        ($_.Contains('horizontal_overflow') -and $_['horizontal_overflow'] -eq $true)
    })
    $Report | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $ReportPath -Encoding utf8
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
Write-Output "Saved new Ver.1 deck: $FinalPptx"
if (-not $SkipPdf) { Write-Output "Saved new Ver.1 PDF: $FinalPdf" }
Write-Output "Private preservation/layout report: $ReportPath"
