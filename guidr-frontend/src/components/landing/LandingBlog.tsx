'use client';

import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

const BLOG_POSTS = [
  {
    id: 1,
    title: 'How to Write a Standout Statement of Purpose',
    description: 'Learn the key elements that make your SOP memorable to admissions committees.',
    date: 'January 15, 2026',
    category: 'Application Tips',
    image: 'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=600&q=80',
    bgClass: 'bg-landingLavender',
  },
  {
    id: 2,
    title: 'Finding the Right Research Advisor: A Complete Guide',
    description: 'Tips for identifying and connecting with faculty members who align with your research interests.',
    date: 'January 8, 2026',
    category: 'Research',
    image: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=600&q=80',
    bgClass: 'bg-landingPeach',
  },
  {
    id: 3,
    title: 'Understanding Graduate School Funding Options',
    description: 'A comprehensive overview of fellowships, assistantships, and grants available to graduate students.',
    date: 'December 28, 2025',
    category: 'Funding',
    image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=600&q=80',
    bgClass: 'bg-landingMint',
  },
];

export function LandingBlog() {
  return (
    <section className="py-20 sm:py-28 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="mb-12">
          <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-display font-semibold text-text leading-tight max-w-2xl">
            We share insights and guides to help you succeed
          </h2>
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 mt-4 text-sm font-medium text-textSecondary hover:text-text transition-colors uppercase tracking-wide"
          >
            Learn more about our resources
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {/* Blog posts grid */}
        <motion.div
          className="grid md:grid-cols-3 gap-6"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
          variants={{
            visible: {
              transition: {
                staggerChildren: 0.12,
                delayChildren: 0.1,
              },
            },
          }}
        >
          {BLOG_POSTS.map((post) => (
            <motion.div key={post.id} variants={{ hidden: { opacity: 0, y: 24 }, visible: { opacity: 1, y: 0 } }} transition={{ duration: 0.5 }}>
              <Link
                href={`/blog/${post.id}`}
                className="group block"
              >
              {/* Stock image */}
              <div className="relative rounded-2xl aspect-[4/3] overflow-hidden mb-4 transition-all duration-300 group-hover:shadow-soft-lg">
                <Image
                  src={post.image}
                  alt={post.title}
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  className="object-cover"
                />
              </div>

              {/* Post content */}
              <h3 className="text-lg font-semibold text-text group-hover:text-textSecondary transition-colors mb-2">
                {post.title}
              </h3>
              <p className="text-sm text-textSecondary line-clamp-2 mb-3">
                {post.description}
              </p>
              <p className="text-xs text-textMuted">{post.date}</p>
            </Link>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
