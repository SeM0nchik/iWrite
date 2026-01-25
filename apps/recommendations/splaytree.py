class Node(object):
    def __init__(self, post_id : int, score : float, parent):
        self.post_id = post_id
        self.score = score
        self.parent : Node  = parent
        self.right : Node  = None
        self.left : Node = None

class SplayTree(object):

    def __init__(self):
        self.root = None

    def rotateRight(self, node : Node):
        if not node or not node.left:
            return

        q = node.left
        parent = node.parent

        node.left = q.right
        if (q.right):
            q.right.parent = node

        q.parent = parent

        if not parent:
            root = q
        elif node == parent.left:
            parent.left = node
        else :
            parent.right = q

        q.right = node
        node.parent = q

    def rotateLeft(self, node : Node):
        if not node or not node.right:
            return

        q = node.right
        parent = node.parent

        node.right = q.left

        if (q.left):
            q.left.parent = node

        q.parent = parent

        if not parent:
            root = q
        elif node == parent.right:
            parent.left = node
        else :
            parent.right = q

        q.left = node
        node.parent = q

    def insert(self, post_id :int, score : float):
        if not self.root:
            self.root = Node(post_id,score, None)
            return

        current : Node = self.root
        while current:
            if score < current.score:
                if not current.left:
                    current.left = Node(post_id,score, current)
                    self.splay(current.left)
                    return
                current = current.left
            elif score > current.score:
                if not current.right:
                    current.right = Node(post_id, score, current)
                    self.splay(current.right)
                    return
                current = current.right
            else:
                return


    def find(self, post_id : int, score : float):
        current : Node = self.root
        while current:
            if current.post_id == post_id and abs(current.score - score) < 0.001:
                return current
            elif score >  current.score:
                current = current.right
            else:
                current = current.left
        return None

    def getHeight(self, node : Node) -> int:
        if not node:
            return -1

        leftHeight = self.getHeight(node.left)
        rightHeight = self.getHeight(node.right)

        return max(leftHeight, rightHeight) + 1

    def height(self) -> int:
        return self.getHeight(self.root)

    def splay(self, node : Node):
        if not node:
            return self.root

        while node != self.root:
            parent : Node = node.parent
            if not parent:
                break

            grandparent = parent.parent

            if not grandparent:
                if node == parent.left:
                    self.rotateRight(parent)
                else :
                    self.rotateLeft(parent)

            elif parent == grandparent.left:
                if node == parent.left:
                    self.rotateRight(grandparent)
                    self.rotateRight(parent)
                else:
                    self.rotateLeft(parent)
                    self.rotateRight(grandparent)
            else:
                if node == parent.right:
                    self.rotateLeft(grandparent)
                    self.rotateLeft(parent)
                else:
                    self.rotateRight(parent)
                    self.rotateLeft(grandparent)
        return self.root

    def clear(self):
        self.root = None

    def delete(self, post_id: int, score: float):
        pass

    def get_top_posts(self, limit: int = 5):
        results = []

        if not self.root:
            return results


        stack = []
        node = self.root

        while node:
            stack.append(node)
            node = node.right

        while stack and len(results) < limit:
            node = stack.pop()
            results.append(node.post_id)

            node = node.left
            while node:
                stack.append(node)
                node = node.right

        return results
