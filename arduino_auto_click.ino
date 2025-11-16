// Arduino HID 鼠标控制：支持点击与相对移动
#include <Mouse.h>

void setup() {
  Serial.begin(115200);
  Mouse.begin();
  delay(1000);
}

// 处理一行命令：
//  - "c"            -> 左键点击
//  - "M dx dy"      -> 相对移动 dx,dy （整数，单位像素）
void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;
  if (line.charAt(0) == 'c') {
    Mouse.press(MOUSE_LEFT);
    delay(random(5, 11));
    Mouse.release(MOUSE_LEFT);
    return;
  }
  if (line.charAt(0) == 'M') {
    int sp1 = line.indexOf(' ');
    int sp2 = line.indexOf(' ', sp1 + 1);
    if (sp1 > 0 && sp2 > sp1) {
      long dx = line.substring(sp1 + 1, sp2).toInt();
      long dy = line.substring(sp2 + 1).toInt();
      // 逐像素/小批次移动，避免加速度导致偏差
      int sx = (dx > 0) ? 1 : -1;
      int sy = (dy > 0) ? 1 : -1;
      long ax = abs(dx);
      long ay = abs(dy);
      long i = 0, j = 0;
      // 若距离较大，使用批次加速：每次移动最多 batch_step 像素
      const int batch_step = 5; // 可调：1=最精确, >1更快但可能受加速度影响
      while (i < ax || j < ay) {
        int mx = 0;
        int my = 0;
        if (i < ax) {
          long remainx = ax - i;
          mx = sx * (remainx >= batch_step ? batch_step : (int)remainx);
          i += (remainx >= batch_step ? batch_step : remainx);
        }
        if (j < ay) {
          long remainy = ay - j;
          my = sy * (remainy >= batch_step ? batch_step : (int)remainy);
          j += (remainy >= batch_step ? batch_step : remainy);
        }
        Mouse.move(mx, my, 0);
        // 小延时保证系统处理，避免合并为大加速度
        delay(1);
      }
    }
    return;
  }
}

void loop() {
  // 读取一行以 '\n' 结束的命令
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    if (line.length() > 0) {
      handleCommand(line);
    }
  }
}
