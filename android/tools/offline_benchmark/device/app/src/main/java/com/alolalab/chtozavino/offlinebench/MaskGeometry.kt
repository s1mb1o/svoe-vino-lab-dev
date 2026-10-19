package com.alolalab.chtozavino.offlinebench

import kotlin.math.*

internal data class Point(val x: Double, val y: Double)
internal data class MaskBounds(val left: Double, val top: Double, val right: Double, val bottom: Double)
internal data class DenseMask(val values: FloatArray, val width: Int, val height: Int,
                              val sourceWidth: Int, val sourceHeight: Int,
                              val originX: Double = 0.0, val originY: Double = 0.0,
                              val stepX: Double = sourceWidth.toDouble()/width,
                              val stepY: Double = sourceHeight.toDouble()/height) {
    init { require(width>0 && height>0 && sourceWidth>0 && sourceHeight>0 && stepX>0 && stepY>0)
        require(values.size == width * height && values.all { it.isFinite() }) }
    val cellWidth get() = stepX
    val cellHeight get() = stepY
    fun sample(x: Double, y: Double, nearest: Boolean = false): Float {
        if (x<0 || y<0 || x>=sourceWidth || y>=sourceHeight) return 0f
        val mx = ((x-originX) / cellWidth - .5).coerceIn(0.0,width-1.0)
        val my = ((y-originY) / cellHeight - .5).coerceIn(0.0,height-1.0)
        fun value(ix: Int, iy: Int): Float = if (ix in 0 until width && iy in 0 until height)
            values[iy * width + ix].coerceIn(0f,1f) else 0f
        if (nearest) return value(floor(mx + .5).toInt(),floor(my + .5).toInt())
        val ix = floor(mx).toInt()
        val iy = floor(my).toInt()
        val fx = mx - ix
        val fy = my - iy
        return ((1-fy)*((1-fx)*value(ix,iy)+fx*value(ix+1,iy)) +
            fy*((1-fx)*value(ix,iy+1)+fx*value(ix+1,iy+1))).toFloat()
    }
    fun hull(): List<Point> {
        val points = mutableSetOf<Point>()
        for (y in 0 until height) {
            val sy = originY+(y+.5)*cellHeight
            if (sy<0 || sy>=sourceHeight) continue
            val active = (0 until width).filter {
                val sx = originX+(it+.5)*cellWidth
                sx>=0 && sx<sourceWidth && values[y * width + it] >= .5f
            }
            if (active.isEmpty()) continue
            for (x in listOf(active.first(),active.last())) points.add(Point(originX+(x+.5)*cellWidth,sy))
        }
        require(points.size >= 3) { "Сегментация не нашла объект." }
        val sorted = points.sortedWith(compareBy<Point> { it.x }.thenBy { it.y })
        fun cross(a: Point,b: Point,c: Point) = (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
        fun half(input: List<Point>): List<Point> {
            val result = mutableListOf<Point>()
            for (point in input) {
                while (result.size >= 2 && cross(result[result.size-2],result.last(),point) <= 0) result.removeAt(result.lastIndex)
                result.add(point)
            }
            return result.dropLast(1)
        }
        return half(sorted)+half(sorted.reversed())
    }
}

internal object MaskGeometry {
    fun bounds(mask: DenseMask, angle: Double, hull: List<Point> = mask.hull()): MaskBounds {
        val c = cos(Math.toRadians(angle))
        val s = sin(Math.toRadians(angle))
        val x = hull.map { it.x*c+it.y*s }
        val y = hull.map { -it.x*s+it.y*c }
        val dx = (abs(c)*mask.cellWidth+abs(s)*mask.cellHeight)/2
        val dy = (abs(s)*mask.cellWidth+abs(c)*mask.cellHeight)/2
        return MaskBounds(x.min()-dx,y.min()-dy,x.max()+dx,y.max()+dy)
    }
    fun guarded(angle: Double): Double {
        val distance = ((angle+45)%90+90)%90-45
        return if (abs(distance)<5) 0.0 else angle
    }
    fun bestAngle(mask: DenseMask): Double {
        val hull = mask.hull()
        fun area(angle: Double): Double {
            val b = bounds(mask,angle,hull)
            return (b.right-b.left)*(b.bottom-b.top)
        }
        val coarse = (0 until 180).map { it * .5 }.minBy(::area)
        val angles = ((-10..10).map { ((coarse+it*.05)%90+90)%90 }+0.0).distinct().sorted()
        var angle = angles.minBy(::area)
        if (area(0.0)<=area(angle)*(1+1e-8)) angle=0.0
        val b = bounds(mask,angle,hull)
        if (b.right-b.left>b.bottom-b.top) angle+=90
        angle=((angle+90)%180+180)%180-90
        if (neckAtBottom(mask,angle)) angle=(angle+360)%360-180
        return angle
    }
    private fun neckAtBottom(mask: DenseMask,angle: Double): Boolean {
        val b=bounds(mask,angle)
        val scale=min(1.0,512/max(b.right-b.left,b.bottom-b.top))
        val width=max(1,round((b.right-b.left)*scale).toInt())
        val height=max(1,round((b.bottom-b.top)*scale).toInt())
        if (height<16 || height<1.35*width) return false
        val c=cos(Math.toRadians(angle));val s=sin(Math.toRadians(angle))
        val widths=IntArray(height)
        for (y in 0 until height) {
            var left=width;var right=-1
            for (x in 0 until width) {
                val xx=b.left+(x+.5)/scale;val yy=b.top+(y+.5)/scale
                if (mask.sample(xx*c-yy*s,xx*s+yy*c,true)>=.5f) {left=min(left,x);right=max(right,x)}
            }
            widths[y]=if(right>=left)right-left+1 else 0
        }
        val occupied=widths.indices.filter { widths[it]>0 }
        if (occupied.isEmpty()) return false
        val cropped=widths.sliceArray(occupied.first()..occupied.last())
        if (cropped.any { it==0 }) return false
        fun band(start: Double,end: Double)=cropped.sliceArray(round(start*cropped.size).toInt() until
            round(end*cropped.size).toInt()).sorted()
        fun median(values: List<Int>): Double = if(values.size%2==1)values[values.size/2].toDouble()
            else (values[values.size/2-1]+values[values.size/2])/2.0
        val top=band(.08,.32);val bottom=band(.68,.92)
        if(top.isEmpty()||bottom.isEmpty())return false
        val tw=median(top);val bw=median(bottom)
        val larger=max(tw,bw);val smaller=min(tw,bw)
        if(smaller/max(1.0,larger)>.72 || larger<.65*width)return false
        val narrow=if(tw<bw)top else bottom
        if(narrow[(.8*(narrow.size-1)).toInt()]>.72*larger)return false
        return bw<tw
    }
}
