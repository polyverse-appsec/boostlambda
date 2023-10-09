def mins_and_secs(time):
    if time >= 60:
        minutes = int(time // 60)
        seconds = time % 60
        return f"{minutes} mins {int(seconds)} secs"
    elif time < 3:
        return f"{time:.3f} secs"
    elif time < 5:
        return f"{time:.2f} secs"
    elif time < 10:
        return f"{time:.1f} secs"
    else:
        return f"{int(time)} secs"
