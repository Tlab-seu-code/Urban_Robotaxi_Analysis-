# ring_with_center_inset.R
suppressPackageStartupMessages({
  library(tidyverse)
  library(cowplot)
  library(scales)
  library(showtext)
  library(sysfonts)
  library(grid)
})

# ---- Calibri 字体设置（全局；按需调整路径）----
add_calibri <- function() {
  sys <- Sys.info()[["sysname"]]
  cand <- list(
    Windows = list(
      regular    = c("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/Calibri.ttf"),
      bold       = c("C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/Calibri Bold.ttf"),
      italic     = c("C:/Windows/Fonts/calibrii.ttf", "C:/Windows/Fonts/Calibri Italic.ttf"),
      bolditalic = c("C:/Windows/Fonts/calibriz.ttf", "C:/Windows/Fonts/Calibri Bold Italic.ttf")
    )
  )
  pick <- function(v) { v <- path.expand(v); v[file.exists(v)][1] }
  paths <- cand[[ifelse(sys %in% names(cand), sys, "Windows")]]
  reg <- pick(paths$regular); bol <- pick(paths$bold)
  ita <- pick(paths$italic);  boi <- pick(paths$bolditalic)
  if (is.na(reg)) stop("未找到 Calibri.ttf，请安装 Calibri 或修改路径。")
  font_add(family = "Calibri", regular = reg,
           bold = ifelse(is.na(bol), reg, bol),
           italic = ifelse(is.na(ita), reg, ita),
           bolditalic = ifelse(is.na(boi), ifelse(is.na(bol), reg, bol), boi))
}
add_calibri()
showtext_auto()
showtext_opts(dpi = 300)

# 全局默认主题/字体
theme_set(theme_minimal(base_size = 8, base_family = "Calibri"))
theme_update(text = element_text(family = "Calibri"))
update_geom_defaults("text",  list(family = "Calibri"))
update_geom_defaults("label", list(family = "Calibri"))

# ---------- 0) 仅外圈使用的“温和压缩”设置 ----------
compress_method <- "power"  # "power" | "asinh" | "none"
lambda          <- 0.5
asinh_scale     <- NA
make_transform <- function(x_sample) {
  if (compress_method == "power") {
    function(z) z^lambda
  } else if (compress_method == "asinh") {
    s <- if (is.na(asinh_scale)) median(x_sample, na.rm = TRUE) else asinh_scale
    s <- ifelse(s <= 0, 1, s); function(z) asinh(z / s)
  } else {
    function(z) z
  }
}

# ---------- 1) 参数 ----------
csv_path   <- "avdata.csv"
col_o_dist <- "起点所属区"
col_period <- "时间段"
TOPK       <- 10
show_legend <- FALSE

# 外圈“组内/组间”间距旋钮
BAR_WIDTH       <- 0.99  # 组内柱宽（越接近1越窄，只留一条细线）
GROUP_GAP_SLOTS <- 3     # 组间空槽数量（越大，组间隔越大）

PERIODS <- c("Morning","Noon","Evening","Night")
COLORS  <- c(Morning="#ABD8E5", Noon="#F9AD95", Evening="#D15354", Night="#5094D5")
LEGEND_LABELS <- c(
  Morning = "Peak hour (Morning)",
  Noon    = "Day",
  Evening = "Peak hour (Evening)",
  Night   = "Night"
)
cn2en <- c(
  "江岸"="Jiang'an", "江汉"="Jianghan", "硚口"="Qiaokou", "汉阳"="Hanyang",
  "武昌"="Wuchang", "青山"="Qingshan", "洪山"="Hongshan", "东西湖"="Dongxihu",
  "汉南"="Hannan", "蔡甸"="Caidian", "江夏"="Jiangxia", "黄陂"="Huangpi",
  "新洲"="Xinzhou", "东湖高新"="DonghuHiTech"
)

map_period4 <- function(x) {
  x <- as.character(x)
  y <- case_when(
    grepl("早|晨|morning|Morning", x, ignore.case = TRUE) ~ "Morning",
    grepl("中|午|平峰|noon|mid|Mid|Noon", x, ignore.case = TRUE) ~ "Noon",
    grepl("晚|峰|eve|Even", x, ignore.case = TRUE) ~ "Evening",
    grepl("夜|凌晨|night|Night", x, ignore.case = TRUE) ~ "Night",
    TRUE ~ x
  )
  factor(y, levels = PERIODS)
}

# ---------- 2) 读数与清洗 ----------
df_raw <- read.csv(csv_path, fileEncoding = "UTF-8", check.names = FALSE)
stopifnot(all(c(col_o_dist, col_period) %in% names(df_raw)))

df_use <- df_raw %>%
  transmute(
    dist_cn = gsub("\\s+", "", .data[[col_o_dist]]),
    dist_cn = gsub("区$", "", dist_cn),
    period  = map_period4(.data[[col_period]])
  ) %>%
  drop_na(period) %>%
  filter(period %in% PERIODS) %>%
  mutate(dist = ifelse(dist_cn %in% names(cn2en), cn2en[dist_cn], dist_cn))

# 区×时段计数
counts <- df_use %>%
  count(period, dist, name = "cnt") %>%
  arrange(period, desc(cnt))

# 外圈压缩函数（仅外圈用）
tf_ring <- make_transform(counts$cnt)

# ---------- 3) 外圈数据（Top-K/period + 排序 + 组内/组间间距） ----------
ring_topk_base <- counts %>%
  group_by(period) %>% slice_head(n = TOPK) %>% ungroup() %>%
  arrange(factor(period, levels = PERIODS), desc(cnt)) %>%
  mutate(label = dist,
         period = factor(period, levels = PERIODS)) %>%
  group_by(period) %>% mutate(k = row_number()) %>% ungroup()

# 在每个时段末尾插入 GROUP_GAP_SLOTS 个“空槽”扩大组间距
ring_with_gap <- ring_topk_base %>%
  group_by(period) %>%
  do({
    df <- .
    gap <- tibble(
      period = df$period[1],
      dist   = NA_character_,
      cnt    = 0,
      label  = "",
      k      = max(df$k) + seq_len(GROUP_GAP_SLOTS)
    )
    bind_rows(df, gap)
  }) %>%
  ungroup() %>%
  arrange(period, k) %>%
  mutate(id = row_number())

N <- nrow(ring_with_gap)

ring_dat <- ring_with_gap %>%
  mutate(
    cnt_t      = tf_ring(cnt),                          # 压缩后的高度（空槽=0）
    angle      = 90 - 360 * (row_number() - 0.5) / N,   # 角度
    hjust      = ifelse(angle < -90 | angle > 90, 1, 0),
    angle_text = ifelse(angle < -90 | angle > 90, angle + 180, angle)
  )

# 洞大小/上界在“压缩尺度”计算
ymax <- max(ring_dat$cnt_t, na.rm = TRUE)
R0   <- ymax * 0.80

# ---------- 4) 外圈环形柱 ----------
inner_ring_col <- "grey20"
inner_ring_lwd <- 0.6

p_ring <- ggplot(ring_dat, aes(x = factor(id), y = cnt_t, fill = period)) +
  geom_col(width = BAR_WIDTH, color = NA) +
  coord_polar(theta = "x", clip = "off") +
  ylim(-R0, ymax) +
  geom_text(aes(label = label,
                y = 0 + ymax * 0.1,
                angle = angle_text, hjust = hjust),
            size = 6.2,  # 修改1：外侧行政区字号 +2（原4.2→6.2）
            color = "black") +
  geom_hline(yintercept = 0, colour = inner_ring_col,
             linewidth = inner_ring_lwd, lineend = "round") +
  scale_fill_manual(values = COLORS, drop = FALSE, labels = LEGEND_LABELS) +
  guides(fill = if (show_legend) "legend" else "none") +
  theme_void(base_family = "Calibri") +
  theme(
    legend.position = if (show_legend) c(.92, .12) else "none",
    legend.title = element_blank(),
    legend.text  = element_text(size = 9)
  )

# ---------- 5) 中心面板数据（原始值，不压缩） ----------
points_df <- counts %>%
  transmute(period = factor(period, levels = PERIODS), value = cnt)

tukey_bounds <- function(v) {
  v <- as.numeric(v)
  if (length(v) == 0) return(c(lo = 0, hi = 0))
  if (length(v) == 1) return(c(lo = v, hi = v))
  q1 <- quantile(v, 0.25, names = FALSE); q3 <- quantile(v, 0.75, names = FALSE)
  iqr <- q3 - q1
  lo <- max(min(v), q1 - 1.5 * iqr)
  hi <- min(max(v), q3 + 1.5 * iqr)
  c(lo = as.numeric(lo), hi = as.numeric(hi))
}
whisk_df <- counts %>%
  group_by(period) %>%
  summarize(lo = tukey_bounds(cnt)[["lo"]],
            hi = tukey_bounds(cnt)[["hi"]],
            .groups = "drop") %>%
  mutate(period = factor(period, levels = PERIODS))

# ---------- 6) 中心面板 ----------
cap_w <- 0.22

p_center <- ggplot(points_df, aes(x = period, y = value)) +
  geom_violin(aes(fill = period),
              width = 0.7, scale = "width", alpha = 0.6,
              color = NA, show.legend = TRUE) +
  geom_linerange(data = whisk_df,
                 aes(x = period, ymin = lo, ymax = hi),
                 linewidth = 0.6, color = "black", inherit.aes = FALSE,
                 show.legend = FALSE) +
  geom_segment(data = whisk_df,
               aes(x = as.numeric(period) - cap_w/2, xend = as.numeric(period) + cap_w/2,
                   y = lo, yend = lo),
               linewidth = 0.6, color = "black", inherit.aes = FALSE) +
  geom_segment(data = whisk_df,
               aes(x = as.numeric(period) - cap_w/2, xend = as.numeric(period) + cap_w/2,
                   y = hi, yend = hi),
               linewidth = 0.6, color = "black", inherit.aes = FALSE) +
  geom_point(aes(fill = period),
             shape = 21, colour = "black", stroke = 0.3,
             alpha = 0.6, size = 1.8,
             position = position_jitter(width = 0.06, height = 0),
             show.legend = FALSE) +
  scale_fill_manual(values = COLORS, breaks = PERIODS, labels = LEGEND_LABELS, drop = FALSE) +
  scale_color_manual(values = COLORS, breaks = PERIODS, guide = "none") +
  scale_x_discrete(labels = LEGEND_LABELS) +
  scale_y_continuous(
    labels = comma,
    breaks = pretty_breaks(n = 4),
    expand = expansion(mult = c(0, 0.06)),
    limits = c(0, NA)
  ) +
  labs(y = "Average order Volume") +
  theme_minimal(base_size = 8, base_family = "Calibri") +
  theme(
    panel.background    = element_rect(fill = "white", colour = NA),
    panel.grid.major.x  = element_blank(),
    panel.grid.minor    = element_blank(),
    axis.title.x        = element_blank(),
    axis.title.y        = element_text(size = 16, face= "bold", margin = margin(r = 4)), # 修改2：标题字号+2（12→14）
    axis.text.x         = element_blank(),
    axis.text.y         = element_text(size = 14), # 修改2：数字字号+2（10→12）
    axis.line           = element_line(colour = "black", linewidth = 0.3),
    axis.ticks          = element_line(colour = "black"),
    plot.margin         = margin(0, 2, 0, 2),
    legend.position     = "none"   # ← 关闭内置图例
  )

# 抽一个不含图例的副本（合成时使用）
p_center_noleg <- p_center


# ---------- 6.1) 抽出图例（横向长条：宽 > 高） ----------
library(gtable)

legend_g <- cowplot::get_legend(
  p_center +
    guides(
      fill = guide_legend(
        title          = NULL,
        byrow          = TRUE,
        label.hjust    = 0,
        label.position = "right",
        # 关键：把宽度设得比高度大（横向长条）
        keywidth       = unit(24, "pt"),
        keyheight      = unit(6,  "pt")
        # 如需一行排布可加：, nrow = 1
      )
    ) +
    theme(
      legend.position      = "right",
      legend.justification = c(1, 1),
      
      # —— 收紧空白
      legend.box.margin    = margin(0, 0, 0, 0),
      legend.margin        = margin(0, 0, 0, 0),
      legend.spacing.x     = unit(2, "pt"),
      legend.spacing.y     = unit(2, "pt"),
      legend.key           = element_rect(fill = NA, colour = NA),
      
      # —— 字体与背景
      legend.text          = element_text(size = 16, face = "bold", family = "Calibri"), # 修改3：图例字号+2（14→16）
      legend.background    = element_rect(fill = "white", color = NA),
      
      # 同步 legend key 的宽/高，避免被其它设置覆盖
      legend.key.width     = unit(16, "pt"),
      legend.key.height    = unit(6,  "pt")
      # 注意：不要设置 legend.key.size（会强制成正方形）
    )
)

# 去掉左侧多余留白列
legend_g$widths[1] <- unit(0, "pt")
legend_g <- gtable::gtable_trim(legend_g)



# ---------- 7) 合成（图例放到整图右上） ----------
hole_frac    <- R0 / (R0 + ymax)
pad          <- 0.92
scale_center <- 0.60
side         <- hole_frac * pad * scale_center

x0 <- 0.5 - side/2
y0 <- 0.5 - side/2
dx <- 0.015
dy <- 0.00
x_shift <- max(0, min(1 - side, x0 - dx))
y_shift <- max(0, min(1 - side, y0 + dy))

p_ring_top <- p_ring + theme(
  plot.background  = element_rect(fill = alpha("white", 0), colour = NA),
  panel.background = element_rect(fill = alpha("white", 0), colour = NA)
)

# 如需给更大的字体留空间，可适当增大 LEG_H
LEG_W <- 0.5
LEG_H <- 0.44  # ↑ 略增高，避免拥挤
LEG_X <- 0.42
LEG_Y <- 0.42

final_plot <- ggdraw() +
  draw_plot(p_center_noleg, x = x_shift, y = y_shift, width = side, height = side) +
  draw_plot(p_ring_top,     x = 0,       y = 0,      width = 1,    height = 1) +
  draw_plot(legend_g,       x = LEG_X,   y = LEG_Y,  width = LEG_W, height = LEG_H)

ggsave("ring_with_center_inset.png", final_plot,
       width = 10.5, height = 10.5, dpi = 300, bg = "white")

# ---------- 8) 导出（无需安装任何额外包） ----------

# 1) PNG（可选）
ggsave("ring_with_center_inset.png", final_plot,
       width = 10.5, height = 10.5, dpi = 300, bg = "white")

# 2) 导出矢量前先关闭 showtext，避免文字被转曲
showtext_auto(FALSE)

## 2.1 PDF（矢量、可编辑；cairo_pdf 不接受 useDingbats 参数）
ggsave("ring_with_center_inset.pdf", final_plot,
       width = 10.5, height = 10.5, units = "in",
       device = function(...){ grDevices::cairo_pdf(...) },
       bg = "white")

## 2.2 透明底 PDF（可选）
ggsave("ring_with_center_inset_transparent.pdf", final_plot,
       width = 10.5, height = 10.5, units = "in",
       device = function(...){ grDevices::cairo_pdf(...) },
       bg = "transparent")

## 2.3 SVG（矢量、可编辑）
ggsave("ring_with_center_inset.svg", final_plot,
       width = 10.5, height = 10.5, units = "in",
       device = function(...){ grDevices::svg(...) },
       bg = "transparent")

# 恢复 showtext
showtext_auto(TRUE)