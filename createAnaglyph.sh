#!/bin/sh
#
# Evan Bollig 4/30/10
#
# Run this from /tmp/<CameraName> with the following options: 
#
# $1 = Camera Name
# $2 = Number of Frames
# $3 = Output Format (i.e., png, jpg, pdf etc)
#
# It will create a new dir /tmp/<CameraName>/ANAGLYPH which will contain 
# the stitched anaglyph sequence to match the left and right sequences 
# already in the directory. 
# 

mkdir -p ANAGLYPH

for ((i=1; i <= $2 ; i++))  # Double parentheses, and "LIMIT" with no "$".
do
  num=`printf "%04d" $i` 
  composite -stereo 0 $1_SLEFT/$1_SLEFT_$num.* $1_SRIGHT/$1_SRIGHT_$num.* ANAGLYPH/ANAGLYPH_$num.$3
done    

