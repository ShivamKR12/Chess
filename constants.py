from panda3d.core import LPoint3

# Define color constants used throughout the chess game.
# Colors are defined as RGBA tuples (red, green, blue, alpha).
BLACK = (0, 0, 0, 1)  # Solid black for dark squares
WHITE = (1, 1, 1, 1)  # Solid white for light squares
HIGHLIGHT = (0, 1, 1, 1)  # Cyan color for highlighting squares
PIECEBLACK = (.15, .15, .15, 1)  # Dark gray for black chess pieces
YELLOW = (1, 1, 0, 1)  # Yellow for highlighting selected piece


def PointAtZ(z, point, vec):
    """
    Calculate the intersection point at a specific Z height along a vector.

    This function is used for 3D picking and placing objects at a certain height.
    It finds where a ray (defined by point and direction vector) intersects
    a horizontal plane at height z.

    Parameters:
    - z: The target Z coordinate (height)
    - point: Starting point of the ray (LPoint3)
    - vec: Direction vector of the ray (LVector3)

    Returns:
    - LPoint3: The intersection point at the specified Z height
    """
    return point + vec * ((z - point.getZ()) / vec.getZ())


def SquarePos(i):
    """
    Convert a square index (0-63) to its 3D world position on the chessboard.

    The chessboard is an 8x8 grid centered at (0,0,0) in world space.
    Each square is 1 unit wide, so positions range from -3.5 to 3.5 in X and Y.

    Parameters:
    - i: Square index from 0 (a1) to 63 (h8)

    Returns:
    - LPoint3: World position of the square's center
    """
    return LPoint3((i % 8) - 3.5, int(i // 8) - 3.5, 0)


def SquareColor(i):
    """
    Determine the color of a chess square based on its index.

    Creates the classic alternating black and white chessboard pattern.
    The pattern depends on both the file (column) and rank (row) to create
    the correct checkerboard effect.

    Parameters:
    - i: Square index from 0 to 63

    Returns:
    - Color tuple: BLACK or WHITE depending on the square's position
    """
    if (i + ((i // 8) % 2)) % 2:
        return BLACK
    return WHITE
