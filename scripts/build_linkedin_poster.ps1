Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$screenshots = Join-Path $root "screenshots"
$outputDir = Join-Path $root "outputs"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$width = 2400
$height = 3000
$poster = New-Object System.Drawing.Bitmap $width, $height
$g = [System.Drawing.Graphics]::FromImage($poster)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

function Color($hex) {
    return [System.Drawing.ColorTranslator]::FromHtml($hex)
}

function Font($size, $style = "Regular") {
    $fontStyle = [System.Drawing.FontStyle]::$style
    return New-Object System.Drawing.Font -ArgumentList "Segoe UI", $size, $fontStyle, ([System.Drawing.GraphicsUnit]::Pixel)
}

function Brush($hex) {
    return New-Object System.Drawing.SolidBrush (Color $hex)
}

function Pen($hex, $size = 1) {
    return New-Object System.Drawing.Pen (Color $hex), $size
}

function FillRect($x, $y, $w, $h, $hex) {
    $brush = Brush $hex
    $g.FillRectangle($brush, $x, $y, $w, $h)
    $brush.Dispose()
}

function DrawText($text, $x, $y, $w, $h, $size, $hex, $style = "Regular", $align = "Near") {
    $font = Font $size $style
    $brush = Brush $hex
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::$align
    $format.LineAlignment = [System.Drawing.StringAlignment]::Near
    $format.Trimming = [System.Drawing.StringTrimming]::Word
    $rect = New-Object System.Drawing.RectangleF $x, $y, $w, $h
    $g.DrawString($text, $font, $brush, $rect, $format)
    $format.Dispose()
    $font.Dispose()
    $brush.Dispose()
}

function DrawImageCover($path, $x, $y, $w, $h) {
    $img = [System.Drawing.Image]::FromFile($path)
    $scale = [Math]::Max($w / $img.Width, $h / $img.Height)
    $sw = [int]($w / $scale)
    $sh = [int]($h / $scale)
    $sx = [int](($img.Width - $sw) / 2)
    $sy = [int](($img.Height - $sh) / 2)
    $src = New-Object System.Drawing.Rectangle $sx, $sy, $sw, $sh
    $dst = New-Object System.Drawing.Rectangle $x, $y, $w, $h
    $g.DrawImage($img, $dst, $src, [System.Drawing.GraphicsUnit]::Pixel)
    $img.Dispose()
}

function DrawImageContain($path, $x, $y, $w, $h, $bg = "#FFFFFF") {
    FillRect $x $y $w $h $bg
    $img = [System.Drawing.Image]::FromFile($path)
    $scale = [Math]::Min($w / $img.Width, $h / $img.Height)
    $dw = [int]($img.Width * $scale)
    $dh = [int]($img.Height * $scale)
    $dx = [int]($x + (($w - $dw) / 2))
    $dy = [int]($y + (($h - $dh) / 2))
    $dst = New-Object System.Drawing.Rectangle $dx, $dy, $dw, $dh
    $g.DrawImage($img, $dst)
    $img.Dispose()
}

function DrawCard($x, $y, $w, $h, $fill = "#FFFFFF", $border = "#D9DEE7") {
    FillRect $x $y $w $h $fill
    $pen = Pen $border 2
    $g.DrawRectangle($pen, $x, $y, $w, $h)
    $pen.Dispose()
}

function DrawMetricCard($x, $y, $w, $h, $value, $label, $accent) {
    DrawCard $x $y $w $h "#FFFFFF" "#DDE3EC"
    FillRect $x $y 12 $h $accent
    DrawText $value ($x + 42) ($y + 24) ($w - 60) 72 54 "#111827" "Bold"
    DrawText $label ($x + 42) ($y + 92) ($w - 60) 78 25 "#4B5563" "Regular"
}

function DrawFlowStep($x, $y, $w, $title, $subtitle, $accent) {
    DrawCard $x $y $w 170 "#FFFFFF" "#CBD5E1"
    FillRect $x $y $w 14 $accent
    DrawText $title ($x + 24) ($y + 34) ($w - 48) 42 31 "#111827" "Bold" "Center"
    DrawText $subtitle ($x + 24) ($y + 82) ($w - 48) 74 21 "#4B5563" "Regular" "Center"
}

$bg = "#F7F8FA"
FillRect 0 0 $width $height $bg

# Header
FillRect 0 0 $width 360 "#111827"
DrawText "BIMOps AI" 110 70 820 90 78 "#FFFFFF" "Bold"
DrawText "Revit to Databricks Lakehouse" 112 160 1020 56 42 "#D1D5DB" "Regular"
DrawText "A BIM data workflow that turns exported Revit schedules into Bronze, Silver, and Gold Delta tables, then surfaces model inventory, program analytics, asset readiness, and metadata quality in a Databricks dashboard." 112 230 1360 90 28 "#E5E7EB" "Regular"

DrawCard 1610 54 660 250 "#FFFFFF" "#FFFFFF"
DrawImageCover (Join-Path $screenshots "cover.jpg") 1620 64 640 230

# Metrics
$metricY = 420
DrawMetricCard 110 $metricY 500 180 "17" "Revit schedule exports" "#2563EB"
DrawMetricCard 650 $metricY 500 180 "5,507" "BIM records processed" "#059669"
DrawMetricCard 1190 $metricY 500 180 "4" "disciplines integrated" "#7C3AED"
DrawMetricCard 1730 $metricY 560 180 "50+" "Gold dashboard tables" "#EA580C"

# Methodology
DrawText "Methodology" 110 675 800 58 44 "#111827" "Bold"
DrawText "The workflow starts with Revit schedules, standardizes metadata into Databricks lakehouse layers, and creates analytics-ready tables for dashboarding and future AI querying." 110 730 1960 64 27 "#4B5563"

$flowY = 830
$stepW = 380
DrawFlowStep 110 $flowY $stepW "Input" "Autodesk Snowdon Towers Revit schedules" "#0E7490"
DrawFlowStep 550 $flowY $stepW "Bronze" "Raw extracted BIM records with source tracking" "#2563EB"
DrawFlowStep 990 $flowY $stepW "Silver" "Cleaned categories, columns, and discipline mapping" "#7C3AED"
DrawFlowStep 1430 $flowY $stepW "Gold" "Inventory, program, MEP, structural, and quality metrics" "#EA580C"
DrawFlowStep 1870 $flowY $stepW "Output" "Databricks SQL dashboard and AI-ready BIM tables" "#059669"

$arrowFont = Font 42 "Bold"
$arrowBrush = Brush "#64748B"
$g.DrawString(">", $arrowFont, $arrowBrush, 500, ($flowY + 64))
$g.DrawString(">", $arrowFont, $arrowBrush, 940, ($flowY + 64))
$g.DrawString(">", $arrowFont, $arrowBrush, 1380, ($flowY + 64))
$g.DrawString(">", $arrowFont, $arrowBrush, 1820, ($flowY + 64))
$arrowFont.Dispose()
$arrowBrush.Dispose()

# Evidence panels
DrawText "Dashboard Outputs" 110 1088 900 58 44 "#111827" "Bold"
DrawText "Gold tables drive sectioned dashboard views: model inventory, building program, envelope and life safety, MEP/structural systems, and BIM data quality." 110 1142 1900 64 27 "#4B5563"

DrawCard 110 1240 1080 540 "#FFFFFF" "#D9DEE7"
DrawText "Model Inventory" 140 1268 500 40 31 "#1D4ED8" "Bold"
DrawImageContain (Join-Path $screenshots "dashboard1.jpg") 140 1320 1020 430 "#FFFFFF"

DrawCard 1210 1240 1080 540 "#FFFFFF" "#D9DEE7"
DrawText "BIM Data Quality" 1240 1268 500 40 31 "#C2410C" "Bold"
DrawImageContain (Join-Path $screenshots "dashboard5.jpg") 1240 1320 1020 430 "#FFFFFF"

DrawCard 110 1830 690 455 "#FFFFFF" "#D9DEE7"
DrawText "Building Program" 140 1858 520 40 29 "#047857" "Bold"
DrawImageContain (Join-Path $screenshots "dashboard2.jpg") 140 1910 630 345 "#FFFFFF"

DrawCard 850 1830 690 455 "#FFFFFF" "#D9DEE7"
DrawText "MEP + Structural" 880 1858 520 40 29 "#6D28D9" "Bold"
DrawImageContain (Join-Path $screenshots "dashboard4.jpg") 880 1910 630 345 "#FFFFFF"

DrawCard 1590 1830 700 455 "#FFFFFF" "#D9DEE7"
DrawText "Revit Model Context" 1620 1858 540 40 29 "#0E7490" "Bold"
DrawImageCover (Join-Path $screenshots "3d.jpg") 1620 1910 640 345

# Bottom narrative
DrawText "What the project demonstrates" 110 2385 900 58 44 "#111827" "Bold"

DrawCard 110 2465 705 250 "#FFFFFF" "#D9DEE7"
FillRect 110 2465 705 12 "#2563EB"
DrawText "Lakehouse Architecture" 145 2502 620 42 31 "#111827" "Bold"
DrawText "Raw BIM schedule exports are organized into Bronze, Silver, and Gold layers so model metadata can be queried and reused like operational data." 145 2560 625 110 25 "#4B5563"

DrawCard 850 2465 705 250 "#FFFFFF" "#D9DEE7"
FillRect 850 2465 705 12 "#059669"
DrawText "Meaningful BIM Metrics" 885 2502 620 42 31 "#111827" "Bold"
DrawText "The dashboard summarizes program area, MEP assets, structural systems, fire-rated doors, and model inventory across multiple disciplines." 885 2560 625 110 25 "#4B5563"

DrawCard 1590 2465 700 250 "#FFFFFF" "#D9DEE7"
FillRect 1590 2465 700 12 "#EA580C"
DrawText "AI-Ready Data Quality" 1625 2502 620 42 31 "#111827" "Bold"
DrawText "Metadata gaps and BIM readiness scores show which categories are complete enough for analytics, operations, and natural-language querying." 1625 2560 620 110 25 "#4B5563"

# Footer
FillRect 0 2870 $width 130 "#111827"
DrawText "Source model: Autodesk Snowdon Towers Revit sample project" 110 2905 1080 42 26 "#E5E7EB"
DrawText "BIMOps AI | Revit schedule exports + Python + Databricks Delta tables + SQL dashboard" 110 2942 1300 36 22 "#9CA3AF"
DrawText "github.com/R-SAMSAMI/bimops-ai" 1600 2918 690 48 31 "#FFFFFF" "Bold" "Far"

$output = Join-Path $outputDir "bimops-ai-linkedin-poster.png"
$poster.Save($output, [System.Drawing.Imaging.ImageFormat]::Png)

$g.Dispose()
$poster.Dispose()

Write-Host $output
